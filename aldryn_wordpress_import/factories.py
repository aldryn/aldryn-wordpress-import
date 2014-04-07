from aldryn_blog.models import Post
from cmsplugin_filer_image.models import FilerImage
from djangocms_text_ckeditor.models import Text


def create_post(post_data):
    post = Post(
        title=post_data['title'],
        lead_in=post_data['content'][:100],
        publication_start=post_data['publication_start'],
        author=post_data['user']
    )
    post.save()
    return post


def create_filer_plugin(filer_image, target_placeholder):
    image_plugin = FilerImage(image=filer_image)
    image_plugin.position = 1
    image_plugin.tree_id = 0
    image_plugin.lft = 0
    image_plugin.rght = 0
    image_plugin.level = 0
    image_plugin.plugin_type = 'FilerImagePlugin'
    image_plugin.language = 'en'
    image_plugin.placeholder = target_placeholder
    image_plugin.save()


def create_text_plugin(content, target_placeholder):
    text = Text(body=content)
    text.position = 0
    text.tree_id = None
    text.lft = None
    text.rght = None
    text.level = None
    text.language = 'en'
    text.plugin_type = 'TextPlugin'
    text.placeholder = target_placeholder
    text.save()
