import json
import os
from base64 import b64encode

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.account.models import User
from apps.recipe.models import Ingredient, Recipe, RecipeSelection
from apps.recipe.tests.factories import CategoryFactory, RecipeFactory, RecipeSelectionFactory


FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.mark.django_db
class TestRecipeViewSet:
    @pytest.yield_fixture(scope='function', autouse=True)
    def setup(self):
        cache.clear()

    def test_can_access_published_recipes_only_when_non_staff_user(self):
        RecipeFactory.create(published=True)
        RecipeFactory.create(published=True)
        RecipeFactory.create(published=False)

        client = APIClient()
        response = client.get(reverse('recipe:recipe-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

    def test_can_access_all_recipes_when_staff_user(self):
        RecipeFactory.create(published=True)
        RecipeFactory.create(published=True)
        RecipeFactory.create(published=False)

        user_data = {
            'email': 'test@test.com',
            'password': 'test',
            'first_name': 'Toto',
        }
        User.objects.create_superuser(**user_data)

        client = APIClient()
        client.login(username=user_data['email'], password=user_data['password'])
        response = client.get(reverse('recipe:recipe-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_can_create_a_new_recipe_when_staff_user(self):
        category_1 = CategoryFactory.create()
        category_2 = CategoryFactory.create(parent=category_1)

        with open(os.path.join(FIXTURE_ROOT, 'recipe.jpg'), 'rb') as main_picture:
            recipe_data = {
                'slug': 'super-recette',
                'title': 'Crêpes',
                'sub_title': 'vegan',
                'full_title': 'Crêpes vegan au chocolat',
                'main_picture': b64encode(main_picture.read()).decode('utf-8'),
                'goal': '2 pers.',
                'preparation_time': 30,
                'categories': [
                    category_1.id,
                    category_2.id
                ],
                'introduction': 'Hello world',
                'composition': [
                    {
                        'ingredients': [
                            {
                                'ingredient': 'Eau',
                            },
                            {
                                'ingredient': 'Olives',
                                'quantity': 2,
                            },
                        ],
                    },
                    {
                        'name': 'Pâte',
                        'ingredients': [
                            {
                                'ingredient': 'Patates',
                                'unit': 'gr',
                                'quantity': 2,
                            },
                            {
                                'ingredient': 'Sucre',
                                'unit': 'gr',
                                'quantity': 3,
                            },
                        ],
                    },
                ],
                'steps': [
                    'Ajouter la farine',
                    'Ajouter le lait végétal',
                ],
                'meta_description': 'Recettes de crêpes vegan',
            }

        user_data = {
            'email': 'test@test.com',
            'password': 'test',
            'first_name': 'Toto',
        }
        User.objects.create_superuser(**user_data)

        client = APIClient()
        client.login(username=user_data['email'], password=user_data['password'])
        response = client.post(
            reverse('recipe:recipe-list'),
            data=json.dumps(recipe_data),
            content_type='application/json',
        )
        assert response.status_code == status.HTTP_201_CREATED

        recipe = Recipe.objects.filter(slug=recipe_data['slug']).first()

        assert recipe is not None

        # Check if the pictures name are equal
        recipe_data.pop('main_picture')
        assert recipe.slug in recipe.main_picture.name

        # Check if the categories are valid
        recipe_data.pop('categories')
        assert category_1 in recipe.categories.all()
        assert category_2 in recipe.categories.all()

        # Check if ingredients exist
        composition = recipe_data.pop('composition')
        for composition_item in composition:
            for ingredient_item in composition_item['ingredients']:
                assert (
                    Ingredient.objects.filter(name=ingredient_item['ingredient'].lower()).first()
                    is not None
                )

        # Check data are well populated
        for key, value in recipe_data.items():
            assert getattr(recipe, key) == value

    @override_settings(DEBUG=True)
    def test_can_cache_results_data_from_detail(self):
        from django.db import connection, reset_queries

        recipe = RecipeFactory.create(published=True)

        client = APIClient()
        client.get(reverse('recipe:recipe-detail', args=(recipe.slug, )))
        assert len(connection.queries) > 0

        reset_queries()

        client.get(reverse('recipe:recipe-detail', args=(recipe.slug, )))
        assert len(connection.queries) == 0

    @override_settings(DEBUG=True)
    def test_can_cache_results_data_from_list(self):
        from django.db import connection, reset_queries

        client = APIClient()
        client.get(reverse('recipe:recipe-list'))
        assert len(connection.queries) > 0

        reset_queries()

        client.get(reverse('recipe:recipe-list'))
        assert len(connection.queries) == 0

    def test_can_increment_view_counter_on_add_view_call(self):
        recipe = RecipeFactory.create(published=True)

        client = APIClient()
        response = client.post(reverse('recipe:recipe-add_view', args=(recipe.slug, )))
        assert response.status_code == status.HTTP_200_OK

        recipe.refresh_from_db()
        assert recipe.views == 1

    def test_cannot_create_a_new_recipe_when_non_staff(self):
        recipe_data = {
            'slug': 'super-recette',
        }

        user_data = {
            'email': 'test@test.com',
            'password': 'test',
            'first_name': 'Toto',
        }
        User.objects.create_user(**user_data)

        client = APIClient()
        client.login(username=user_data['email'], password=user_data['password'])
        response = client.post(reverse('recipe:recipe-list'), recipe_data, format='multipart')

        assert response.status_code == status.HTTP_403_FORBIDDEN

        recipe = Recipe.objects.filter(slug=recipe_data['slug']).first()
        assert recipe is None


@pytest.mark.django_db
class TestCategoryViewSet:
    def test_can_access_all_categories(self):
        category_1 = CategoryFactory.create()
        CategoryFactory.create(parent=category_1)
        CategoryFactory.create(parent=category_1)
        CategoryFactory.create()

        client = APIClient()
        response = client.get(reverse('recipe:category-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestRecipeSelectionViewSet:
    @pytest.yield_fixture(scope='function', autouse=True)
    def setup(self):
        cache.clear()

    def test_cannot_access_published_selections_only_when_non_staff_user(self):
        RecipeSelectionFactory.create(published=True)
        RecipeSelectionFactory.create(published=True)
        RecipeSelectionFactory.create(published=False)

        client = APIClient()
        response = client.get(reverse('recipe:selection-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

    def test_can_access_all_selections_when_staff_user(self):
        RecipeSelectionFactory.create(published=True)
        RecipeSelectionFactory.create(published=True)
        RecipeSelectionFactory.create(published=False)

        user_data = {
            'email': 'test@test.com',
            'password': 'test',
            'first_name': 'Toto',
        }
        User.objects.create_superuser(**user_data)

        client = APIClient()
        client.login(username=user_data['email'], password=user_data['password'])
        response = client.get(reverse('recipe:selection-list'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_can_create_a_new_selection_when_staff_user(self):
        recipe_1 = RecipeFactory.create(published=True)
        recipe_2 = RecipeFactory.create(published=True)

        with open(os.path.join(FIXTURE_ROOT, 'recipe.jpg'), 'rb') as picture:
            selection_data = {
                'slug': 'super-selection',
                'title': 'Noël',
                'picture': b64encode(picture.read()).decode('utf-8'),
                'recipes': [
                    {
                        'recipe': str(recipe_1.id),
                        'order': 1,
                    },
                    {
                        'recipe': str(recipe_2.id),
                        'order': 2,
                    },
                ],
                'description': 'Hello world',
                'meta_description': 'Recettes de crêpes vegan',
            }

            user_data = {
                'email': 'test@test.com',
                'password': 'test',
                'first_name': 'Toto',
            }
            User.objects.create_superuser(**user_data)

            client = APIClient()
            client.login(username=user_data['email'], password=user_data['password'])
            response = client.post(
                reverse('recipe:selection-list'),
                data=json.dumps(selection_data),
                content_type='application/json',
            )
            assert response.status_code == status.HTTP_201_CREATED

            selection = RecipeSelection.objects.filter(slug=selection_data['slug']).first()

            assert selection is not None
