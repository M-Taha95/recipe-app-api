"""
Test an Ingredient API.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from app.recipe.test.test_recipe_api import create_user
from core.models import Ingredient
from recipe.serializers import IngredientSerializer

INGREDIENT_URL = reverse("recipe:ingredient-list")


def detial_url(ingredient_id):
    """Create and return ingredient URL."""
    return reverse("recipe:ingredient-detail", args=[ingredient_id])


def create_useR(email="test@example.com", password="testpass123"):
    """Creating and return a new user."""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientTest(TestCase):
    """Test unauthenticated for retrieveing an ingredients."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientTest(TestCase):
    """Test Authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@example.com",
            "testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_ingredients(self):
        """Test a retrieveing a list of an ingredients."""
        Ingredient.objects.create(user=self.user, name="Kali")
        Ingredient.objects.create(user=self.user, name="Ubuntu")

        res = self.client.get(INGREDIENT_URL)
        ingredient = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredient, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredient_list_limied_to_user(self):
        """Test list of an ingredients is limited to authenticated users."""
        user2 = create_user(email="user2@example.com")
        Ingredient.objects.create(email=user2, name="Salt")
        ingredient = Ingredient.objects.create(user=self.user, name="Pepper")

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], ingredient.name)
        self.assertEqual(res.data[0]["id"], ingredient.id)
