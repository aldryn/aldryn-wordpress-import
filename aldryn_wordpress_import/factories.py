from aldryn_blog.models import Post
from cmsplugin_filer_image.models import FilerImage
from djangocms_text_ckeditor.models import Text
from django.template.defaultfilters import truncatewords_html
from django.template.defaultfilters import slugify


def create_post(post_data, parts):
    try:
        first_part = parts[0]
    except IndexError:
        first_part = post_data['title']
    slug = slugify(post_data['title'])
    post_with_slug = Post.objects.filter(slug=slug)
    if post_with_slug.exists():
        raise ValueError('Slug is not unique')
    post = Post(
        title=post_data['title'],
        slug=slug,
        lead_in=truncatewords_html(first_part, 10),
        publication_start=post_data['publication_start'],
        author=post_data['user']
    )
    post.save()
    return post


def create_filer_plugin(filer_image, target_placeholder, language):
    image_plugin = FilerImage(image=filer_image)
    image_plugin.position = 0
    image_plugin.tree_id = 0
    image_plugin.lft = 0
    image_plugin.rght = 0
    image_plugin.level = 0
    image_plugin.plugin_type = 'FilerImagePlugin'
    image_plugin.language = language
    image_plugin.placeholder = target_placeholder
    image_plugin.save()


def create_text_plugin(content, target_placeholder, language):
    text = Text(body=content)
    text.position = 0
    text.tree_id = None
    text.lft = None
    text.rght = None
    text.level = None
    text.language = language
    text.plugin_type = 'TextPlugin'
    text.placeholder = target_placeholder
    text.save()
