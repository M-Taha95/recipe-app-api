"""
Test Tag API.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Tag, Recipe
from recipe.serializers import TagSerializer
from decimal import Decimal

TAGS_URL = reverse("recipe:tag-list")


def detail_url(tag_id):
    """Create and return tga datial URL."""
    return reverse("recipe:tag-detail", args=[tag_id])


def create_user(email="test@example.com", password="testpass123"):
    """Creating and return a new user."""
    return get_user_model().objects.create_user(
        email=email, password=password
    )


class PublicTagApiTest(TestCase):
    """Test unauthenticated for retrieveing tags"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagApiTest(TestCase):
    """Test Authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@example.com", "testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_tags(self):
        """Test a retrieveing a list of tags."""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Desert")

        res = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by("-name")
        seralizer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, seralizer.data)

    def test_tags_list_limited_to_user(self):
        """Test list of tags is limited to authenticated users."""
        other_user = get_user_model().objects.create_user(
            "other@example.com",
            "password123",
        )
        Tag.objects.create(user=other_user, name="Fruity")
        tags = Tag.objects.create(user=self.user, name="Comfort Food")
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["name"], tags.name)
        self.assertEqual(res.data[0]["id"], tags.id)

    def test_update_tag(self):
        """Test update tags."""
        tag = Tag.objects.create(user=self.user, name="After Dinner")
        payload = {"name": "Desert"}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload["name"])

    def test_delete_tags(self):
        """Test deleting a tag."""
        tag = Tag.objects.create(user=self.user, name="Breakfast")

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test listing tags to those assigned to recipes."""
        tag1 = Tag.objects.create(user=self.user, name="Breakfast")
        tag2 = Tag.objects.create(user=self.user, name="Lunch")
        recipe = Recipe.objects.create(
            title="Green Eggs on Toast",
            time_minutes=10,
            price=Decimal("2.50"),
            user=self.user,
        )
        recipe.tag.add(tag1)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """Test filtering tags returns a unique list."""
        tag = Tag.objects.create(user=self.user, name="Breakfast")
        Tag.objects.create(user=self.user, name="Dinner")
        recipe1 = Recipe.objects.create(
            title="Panckaes",
            time_minutes=5,
            price=Decimal("5.00"),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title="Porrige",
            time_minutes=3,
            price=Decimal("2.00"),
            user=self.user,
        )
        recipe1.tag.add(tag)
        recipe2.tag.add(tag)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})
        self.assertEqual(len(res.data), 1)
        
