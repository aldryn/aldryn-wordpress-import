from aldryn_blog.models import Post


def create_post(post_data):
    post = Post(
        title=post_data['title'],
        lead_in=post_data['content'][:100],
        publication_start=post_data['publication_start'],
    )

