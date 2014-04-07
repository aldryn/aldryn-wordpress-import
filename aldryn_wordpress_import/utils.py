from collections import defaultdict
from datetime import datetime, timedelta
from easy_thumbnails.files import get_thumbnailer
import feedparser
import os
import re
import requests
import uuid
import urllib2
from time import mktime, timezone
from xml.dom.minidom import parse

from django.core.files.storage import default_storage
from django.core.files import File
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.html import linebreaks
from filer.models import Image
from BeautifulSoup import BeautifulSoup


# from future.builtins import int


class WordpressParser(object):
    base_url = None

    def parse(self, file_path):
        if file_path is None:
            raise RuntimeError("Missing file path")

        feed = feedparser.parse(file_path)
        xml = parse(file_path)
        xmlitems = xml.getElementsByTagName("item")
        self.base_url = feed['channel']['wp_base_site_url']

        for (i, entry) in enumerate(feed["entries"]):
            # Get a pointer to the right position in the minidom as well.
            xmlitem = xmlitems[i]
            content = linebreaks(self.wp_caption(entry.content[0]["value"]))
            content = self.handle_images(content)

            # Get the time struct of the published date if possible and
            # the updated date if we can't.
            pub_date = getattr(entry, "published_parsed", entry.updated_parsed)
            pub_date = datetime.fromtimestamp(mktime(pub_date))
            pub_date -= timedelta(seconds=timezone)

            # Tags and categories are all under "tags" marked with a scheme.
            terms = defaultdict(set)
            for item in getattr(entry, "tags", []):
                terms[item.scheme].add(item.term)

            if entry.wp_post_type == "post":
                post = dict(title=entry.title, content=content,
                            publication_start=pub_date, tags=terms["tag"],
                            old_url=entry.id)

                # Do something

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

    def handle_images(self, post):
        """
        Find direct image links. Check for thumbnails and create
        filer thumbnails
        """

        soup = BeautifulSoup(post)
        links = soup.findAll("a")
        internal_uploads_dir = '{}/wp-content/uploads'.format(self.base_url)
        content = post
        for link in links:
            href = link['href']
            if internal_uploads_dir in href:
                replace_dict = {}
                big_image = self.download_and_save(href)
                big_image_new = self.construct_url(big_image)
                replace_dict[href] = big_image_new

                thumbnail = link.find('img')
                if thumbnail:
                    old_url = thumbnail['src']
                    new_thumb = self.handle_thumbnail(thumbnail, big_image)
                    new_url = self.construct_url(new_thumb)
                    replace_dict[old_url] = new_url

                content = self.replace_items(replace_dict, content)

        return content

    def handle_thumbnail(self, img_tag, filer_image):
        thumbnailer = get_thumbnailer(filer_image)
        try:
            height = img_tag['height']
            width = img_tag['width']
        except KeyError:
            # No dimensions, get some defaults
            width = 300
            height = 225
        thumb = thumbnailer.get_thumbnail({'size': (width, height),
                                           'crop': True})
        return thumb

    def download_and_save(self, file_url):
        response = requests.get(file_url, stream=True)
        file_name = urllib2.unquote(file_url).decode('utf8').split('/')[-1]
        file_extension = file_name.split('.')[-1]
        tmp_name = "{}.{}".format(str(uuid.uuid1()), file_extension)
        tmp_name = default_storage.save(tmp_name,
                                        ContentFile(response.content))
        tmp_path = '{}/{}'.format(settings.MEDIA_ROOT, tmp_name)
        saved_file = File(open(tmp_path))

        filer_img = Image.objects.create(original_filename=file_name,
                                         file=saved_file)
        os.remove(tmp_path)
        return filer_img

    def construct_url(self, filer_image):
        site = Site.objects.get_current()
        url = 'http://{}{}'.format(site.domain, filer_image.url)
        return url

    def replace_items(self, replace_dict, content):
        for key in replace_dict:
            content = content.replace(key, replace_dict[key])
        return content

