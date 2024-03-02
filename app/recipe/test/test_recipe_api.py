"""
Test recipe API.
"""

import os
import tempfile
from PIL import Image
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    """Create and return recipe detail URL"""
    return reverse("recipe:recipe-detail", args= [recipe_id])


def image_upload_url(recipe_id):
    """Create and return image upload URL."""
    return reverse("recipe:recipe-upload-image", args= [recipe_id])


def create_recipe(user, **params):
    """Create and return recipes."""
    defaults = {
        "title": "sample recipe title",
        "time_minutes": 22,
        "price": Decimal("5.25"),
        "description": "sample recipe description",
        "link": "http://example.com/recipe.pdf",
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user= user, **defaults)
    return recipe


def create_user(self, **params):
    """Test for creating and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTest(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTest(TestCase):
    """Test Authentiacted API requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@example.com",
            "testpass123",
        )
        self.client.force_authenticate(user= self.user)

    def test_retrieve_recipe(self):
        """Test a retrieveing a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)
        recipe = Recipe.objects.all().order_by("-id")
        seralizer = RecipeSerializer(recipe, many= True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, seralizer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated users."""
        other_user = get_user_model().objects.create_user(
            "other@example.com",
            "password123",
        )
        create_recipe(user= other_user)
        create_recipe(user= self.user)
        res = self.client.get(RECIPE_URL)

        recipe = Recipe.objects.filter(user= self.user)
        serializer = RecipeSerializer(recipe, many= True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            "title": "sample recipe",
            "time_minutes": 30,
            "price": Decimal("5.99"),
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id= res.data["id"])
        for key, value in payload.items():
            self.assertEqual(getattr(recipe, key), value)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partisl update of a recipe."""
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user= self.user,
            title= "Sample recipe title",
            link= original_link,
        )

        payload = {"title": "New recipe title"}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    # def test_create_recipe_with_new_tags(self):
    #     """Test creating a recipe with new tags."""
    #     payload = {
    #         "title": "Thai Prawn Curry",
    #         "time_minute": 30,
    #         "price": Decimal("2.50"),
    #         "tags": [{"name": "Thai"}, {"name": "Dinner"}],
    #     }
    #     res = self.client.post(RECIPE_URL, payload, format="json")

    #     self.assertEqual(res.status_code, status.HTTP_201_CREATED)
    #     recipes = Recipe.objects.filter(user=self.user)
    #     self.assertEqual(recipes.count(), 1)
    #     recipe = recipes[0]
    #     self.assertEqual(recipe.tag.count(), 2)
    #     for tag in payload["tags"]:
    #         exists = recipe.tag.filter(
    #             name=tag["name"],
    #             user=self.user,
    #         ).exists()
    #         self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_indian = Tag.objects.create(user= self.user, name= "Indian")
        payload = {
            "title": "Pongal",
            "time_minutes": 60,
            "price": Decimal("4.50"),
            "tags": [{"name": "Indian"}, {"name": "Breakfast"}],
        }
        res = self.client.post(RECIPE_URL, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user= self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tag.count(), 2)
        self.assertIn(tag_indian, recipe.tag.all())
        for tag in payload["tags"]:
            exists = recipe.tag.filter(name= tag["name"], user= self.user).exists()
            self.assertTrue(exists)

    def test_creste_tag_on_update(self):
        """Test creating ta when updating a recipe."""
        recipe = create_recipe(user= self.user)

        payload = {"tags": [{"name": "Lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user= self.user, name= "Lunch")
        self.assertIn(new_tag, recipe.tag.all())

    def test_update_recipe_assign_tag(self):
        """Test assigining an existing ta when updating a recipe."""
        tag_breakfast = Tag.objects.create(
            user= self.user, name= "Breakfast"
        )
        recipe = create_recipe(user= self.user)
        recipe.tag.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user= self.user, name= "Lunch")
        payload = {"tags": [{"name": "Lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tag.all())
        self.assertNotIn(tag_breakfast, recipe.tag.all())

    def test_clear_recipe_tags(self):
        """Test clearing a recipe tags."""
        tag = Tag.objects.create(user= self.user, name= "Desert")
        recipe = create_recipe(user= self.user)
        recipe.tag.add(tag)

        payload = {"tags": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tag.count(), 0)

    # def test_create_recipe_with_new_ingredients(self):
    #     """Test creating a recipe with new ingredients."""
    #     payload = {
    #         'title': 'Caulifolwer Tacos',
    #         'time_minute': 60,
    #         'price': Decimal('4.30'),
    #         'ingedients': [{'name':'Cauliflower'}, {'name': 'Salt'}]
    #     }
    #     res = self.client.post(RECIPE_URL, payload, format='json')
    #     self.assertEqual(res.status_code, status.HTTP_201_CREATED)
    #     recipes = Recipe.objects.filter(user=self.user)
    #     self.assertEqual(recipes.count(), 1)
    #     recipe = recipes[0]
    #     self.assertEqual(recipe.ingredient.count(), 2)
    #     for ingredient in payload['ingedients']:
    #         exists = recipe.ingredient.filter(
    #             name = ingredient['name'],
    #             user = self.user,
    #         ).exists()
    #         self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a new recipe with existing ingredinet."""
        ingredient = Ingredient.objects.create(
            user= self.user, name= "Lemon"
        )
        payload = {
            "title": "Vietnamese Soup",
            "time_minutes": 25,
            "price": Decimal("2.55"),
            "ingredients": [{"name": "Lemon"}, {"name": "Fish Souce"}],
        }
        res = self.client.post(RECIPE_URL, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user= self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredient.count(), 2)
        self.assertIn(ingredient, recipe.ingredient.all())
        for ingredient in payload["ingredients"]:
            exists = recipe.ingredient.filter(
                name= ingredient["name"],
                user= self.user,
            ).exists()
            self.assertTrue(exists)

    def test_creste_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)

        payload = {"ingredients": [{"name": "Limes"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingeredient = Ingredient.objects.get(
            user= self.user, name= "Limes"
        )
        self.assertIn(new_ingeredient, recipe.ingredient.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigining an existing an ingredient when updating a recipe."""
        ingredient1 = Ingredient.objects.create(
            user= self.user, name= "Pepper"
        )
        recipe = create_recipe(user= self.user)
        recipe.ingredient.add(ingredient1)

        ingredient2 = Ingredient.objects.create(
            user= self.user, name= "Chili"
        )
        payload = {"ingredients": [{"name": "Chili"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredient.all())
        self.assertNotIn(ingredient1, recipe.ingredient.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipe ingredients."""
        ingredient = Ingredient.objects.create(
            user= self.user, name= "Garlic"
        )
        recipe = create_recipe(user= self.user)
        recipe.ingredient.add(ingredient)

        payload = {"ingredients": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format= "json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredient.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering recipes by tags."""
        r1 = create_recipe(
            user= self.user, title= "Thai Vegetable Curry"
        )
        r2 = create_recipe(
            user= self.user, title= "Aubergine with Tahini"
        )
        tag1 = Tag.objects.create(
            user= self.user, name= "Vegan"
        )
        tag2 = Tag.objects.create(
            user= self.user, name= "Vegetable"
        )
        r1.tag.add(tag1)
        r2.tag.add(tag2)
        r3 = create_recipe(
            user= self.user, title= "Fish and Chips"
        )

        params = {"tag": f"{tag1.id}, {tag2.id}"}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredient(self):
        """Test filtering recipes by ingredients."""
        r1 = create_recipe(
            user= self.user, title= "Posh Beans on Toast"
        )
        r2 = create_recipe(
            user= self.user, title= "Chicken Cacciatore"
        )
        ingredient1 = Ingredient.objects.create(
            user= self.user, name= "Feta Cheese"
        )
        ingredient2 = Ingredient.objects.create(
            user= self.user, name= "Chiken"
        )
        r1.ingredient.add(ingredient1)
        r2.ingredient.add(ingredient2)
        r3 = create_recipe(
            user= self.user, title= "Red Lentil dal"
        )

        params = {"ingredient": f"{ingredient1.id}, {ingredient2.id}"}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@example.com",
            "pass123",
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user= self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix= ".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format= "JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format= "multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {"image": "notanimage"}
        res = self.client.post(url, payload, format= "multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
