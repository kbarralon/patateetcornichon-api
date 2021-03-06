from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.forms import model_to_dict
from django.utils.html import strip_tags
from django.utils.text import Truncator

from apps.comment.models import Comment
from apps.story.files import story_main_picture_directory_path
from common.db.abstract_models import PostModel, SlugModel


class Story(PostModel):
    """ A nice word to represent a post blog. """

    # The picture illustration of the blog post
    main_picture = models.ImageField(upload_to=story_main_picture_directory_path)

    # Content - Have to be HTML Content
    content = models.TextField()

    # A Story should have one or multiple tags linked
    tags = models.ManyToManyField('Tag')

    # We could have multiple users on stories
    authors = models.ManyToManyField('account.User', related_name='stories')

    comments = GenericRelation(Comment, related_query_name='story')

    @property
    def tags_list(self):
        """ Return tags fields in a dictionary. """
        return [
            model_to_dict(tag, fields=['slug', 'name'])
            for tag in self.tags.all()
        ]

    @property
    def content_preview(self):
        """ Return a content preview of the HTML content """
        content_without_html = strip_tags(self.content)
        return Truncator(content_without_html).chars(300)


class Tag(SlugModel):
    """ This Tag model is referenced inside the Story model. """

    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
