from __future__ import unicode_literals
import re
import uuid
import urllib2
import StringIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.html import linebreaks
from django.contrib.sites.models import Site
from django.utils.text import slugify

from dateutil import parser
from BeautifulSoup import BeautifulSoup
import requests
from lxml import etree
from filer.models import Image
from taggit.models import Tag
from aldryn_blog.models import Category
from cms.plugin_pool import plugin_pool

from . import factories


class WordpressParser(object):
    base_url = None
    data = None
    language = None

    # namespaces
    ns = {
        'content': '{http://purl.org/rss/1.0/modules/content/}',
        'dc': '{http://purl.org/dc/elements/1.1/}',
        'wp': '{http://wordpress.org/export/1.2/}',
    }

    available_authors = None
    available_tags = None
    available_categories = None

    image_placeholder = str(uuid.uuid1())

    def __init__(self, wp_import):
        self.wp_import = wp_import
        self.file_path = self.wp_import.xml_file.path
        self.language = self.wp_import.target_language
        self.site = Site.objects.get_current()

    def parse(self, instance):
        if self.file_path is None:
            raise RuntimeError("Missing file path")

        tree = etree.parse(self.file_path)
        log, success, skipped, failed = [], [], [], []

        self.data = tree.find('channel')
        self.base_url = self.data.find('%sbase_site_url' % self.ns['wp']).text
        # self.language = self.data.find('language').text.split('-')[0]  # assuming 'en-US' or 'de-DE'

        self.available_authors = self.find_terms('%sauthor' % self.ns['wp'], 'author_login')
        self.available_tags = self.find_terms('%stag' % self.ns['wp'], 'tag_name')
        self.available_categories = self.find_terms('%scategory' % self.ns['wp'], 'category_nicename')

        # Before creating cms plugins we have to make
        # sure all are loaded and ready to use
        plugin_pool.get_all_plugins()

        all_entries = self.data.findall('item')

        for entry in all_entries:
            entry_title = entry.find('title').text
            entry_type = entry.find('%spost_type' % self.ns['wp']).text

            if entry_type != 'post':
                skipped.append('%s skipped (entry type is %s)' % (entry_title, entry_type))
                continue

            content = linebreaks(entry.find('%sencoded' % self.ns['content']).text)
            entry_content, entry_images = self.extract_images(content)

            if entry.find('%sstatus' % self.ns['wp']).text == 'draft':
                skipped.append('%s skipped (draft post)' % entry_title)
                continue

            entry_pub_date = parser.parse(entry.find('pubDate').text)

            # author
            entry_author_loginid = \
                entry.find('%screator' % self.ns['dc']).text or entry.find('category[@domain="author"]').text
            entry_author_raw = self.available_authors[entry_author_loginid]
            entry_author, _ = User.objects.get_or_create(username=entry_author_raw['author_login'])
            changed = False
            for field in ['email', 'first_name', 'last_name']:
                if not getattr(entry_author, field, None):
                    setattr(entry_author, field, entry_author_raw['author_%s' % field])
                    changed = True

            if changed:
                entry_author.save()

            # category
            # aldryn-blog only supports one category, WP multiple. we use the first one given and log a warning
            # concerning the remaining categories
            entry_category = None
            entry_categories = []
            categories_used = entry.findall('category[@domain="category"]')

            for each in categories_used:
                if each.get('nicename') in self.available_categories:
                    entry_categories.append(each)
                    if not entry_category:
                        try:
                            entry_category = Category.objects.get(translations__name=each.get('nicename'))
                        except Category.DoesNotExist:
                            entry_category = Category()
                            entry_category.translate(language_code=self.language)
                            entry_category.name = each.get('nicename')
                            entry_category.slug = slugify(unicode(each.get('nicename')))
                            entry_category.save()

                # TODO: show warning for rest of categories

            # tags
            entry_tags = []
            tags_used = entry.findall('category[@domain="post_tag"]')
            for each in tags_used:
                if each.get('nicename') in self.available_tags:
                    tag_raw = self.available_tags[each.get('nicename')]
                    tag, _ = Tag.objects.get_or_create(name=tag_raw['tag_name'], slug=tag_raw['tag_slug'])
                    entry_tags.append(tag)

            # slug
            entry_slug = entry.find('%spost_name' % self.ns['wp']).text

            # wp link
            link = entry.find('link').text

            post = dict(
                title=entry_title,
                content=entry_content,
                publication_start=entry_pub_date,
                tags=entry_tags,
                category=entry_category,
                images=entry_images,
                user=entry_author,
                slug=entry_slug,
                language=self.language,
                link=link,
            )

            result, status = self.create_post(post)
            if status:
                success.append(result)
            else:
                failed.append(result)

        log.extend(success)
        log.extend(skipped)
        log.extend(failed)
        summary = '{} posts imported, {} skipped, {} failed, {} total'.format(len(success), len(skipped), len(failed), len(all_entries))
        log.append(summary)
        return '\n'.join(log)

    def wp_caption(self, post):
        """
        Filters a Wordpress Post for Image Captions and renders to
        match HTML.
        """
        for match in re.finditer(r"\[caption (.*?)\](.*?)\[/caption\]", post):
            meta = '<div '
            caption = ''
            for imatch in re.finditer(r'(\w+)="(.*?)"', match.group(1)):
                if imatch.group(1) == 'id':
                    meta += 'id="%s" ' % imatch.group(2)
                if imatch.group(1) == 'align':
                    meta += 'class="wp-caption %s" ' % imatch.group(2)
                if imatch.group(1) == 'width':
                    width = int(imatch.group(2)) + 10
                    meta += 'style="width: %spx;" ' % width
                if imatch.group(1) == 'caption':
                    caption = imatch.group(2)
            parts = (match.group(2), caption)
            meta += '>%s<p class="wp-caption-text">%s</p></div>' % parts
            post = post.replace(match.group(0), meta)
        return post

    def extract_images(self, post):
        """
        Finds direct image links. Creates filer Image objects
        and extracts links
        """
        soup = BeautifulSoup(post)
        links = soup.findAll("img")
        internal_uploads_dir = '{}/wp-content/uploads'.format(self.base_url)
        images = []
        for link in links:
            try:
                href = link['src']
            except KeyError:
                # Link has no href
                continue
            if internal_uploads_dir in href:
                if not Image.matches_file_type(href, None, None):
                    # File is not an image
                    continue
                image = self.download_and_save(href)
                images.append(image)
                # Remove link from content, replace with placeholder
                link.replaceWith(self.image_placeholder)

            # Re-write all internal links - GH: #3
            if self.site.domain in href:
                uri = href.split(self.site.domain)[1]
                link['href'] = uri

        return str(soup), images

    def download_and_save(self, file_url):
        response = requests.get(file_url)
        file_name = urllib2.unquote(file_url.encode('utf-8')).decode('utf8').split('/')[-1]
        file_extension = file_name.split('.')[-1]
        io = StringIO.StringIO()
        io.write(response.content)
        saved_file = InMemoryUploadedFile(io, None, file_name, file_extension,
                                          io.len, None)
        filer_img = Image.objects.create(original_filename=file_name,
                                         file=saved_file)
        return filer_img

    def create_post(self, post_data):
        post_parts = post_data['content'].split(self.image_placeholder)
        try:
            post = factories.create_post(post_data, parts=post_parts)
            # Post already exists
        except ValueError:
            return "Post with slug {} already exists. Skipping".format(
                post_data['title']), False
        key_visual = None
        for number, part in enumerate(post_parts):
            factories.create_text_plugin(part, post.content, self.language)
            try:
                image = post_data['images'][number]
            except IndexError:
                continue
            else:
                if not key_visual:
                    key_visual = image
                else:
                    factories.create_filer_plugin(image, post.content, self.language)
        post.key_visual = key_visual
        post.category = post_data['category']
        for tag in post_data['tags']:
            post.tags.add(tag)

        # app data field for wp import info
        if hasattr(post, 'app_data'):
            post.app_data.wp_import.link = post_data['link']

        post.save()

        return "Imported post {}".format(post_data['title']), True

    def find_terms(self, lookup, key_field='term_id'):
        results = {}
        entities = self.data.findall('%s' % lookup)
        for entity in entities:
            result = {}
            for child in entity.getchildren():
                result[child.tag.replace(self.ns['wp'], '')] = child.text
            result_key = entity.find('%s%s' % (self.ns['wp'], key_field)).text
            result_key = int(result_key) if result_key.isdigit() else result_key
            results[result_key] = result
        return results
