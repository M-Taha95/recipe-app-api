""" Sample tests """

from django.test import SimpleTestCase

from app import clac


class CalcTest(SimpleTestCase):
    """test the calc module"""

    def test_add_numbers(self):
        """test adding numbers together"""
        res = clac.add(5, 5)

        self.assertEqual(res, 10)

    def test_subtract_numbers(self):
        """test subtracting numbers"""
        res = clac.subtract(10, 15)

        self.assertEqual(res, 5)
