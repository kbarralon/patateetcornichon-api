from algoliasearch_django import AlgoliaIndex
from algoliasearch_django.decorators import register

from .models import Recipe


@register(Recipe)
class RecipeIndex(AlgoliaIndex):
    """ Index representing published recipe. """

    index_name = 'recipe'
    should_index = 'published'
    fields = (
        'slug',
        'title',
        'sub_title',
        'full_title',
        'introduction',
        'main_picture_thumbs',
        'created',
        'comments_count',
        'total_time',
        'tags_list',
        'categories_list',
    )
    settings = {
        'searchableAttributes': [
            'full_title',
            'tags_list',
            'categories_list',
        ],
        'attributesForFaceting': [
            'categories_list.slug',
            'tags_list.slug',
        ],
        'replicas': [
            'recipe_created_asc',
            'recipe_created_desc',
        ],
    }
