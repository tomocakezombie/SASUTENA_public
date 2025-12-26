from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, time, date

from django.contrib.auth import get_user_model

from product.models import Product, TagType
from product.forms import ProductForm
from product.views import get_expiring_products

from django.urls import reverse
from product.models import ProductApplication, Product


class ProductAppTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="prod", password="pw", role="producer")

        now = timezone.now()
        self.product = Product.objects.create(
            item_name="TestItem",
            number=3,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=2),
            description="desc",
            user=self.user,
            publish=True,
            valid=True,
        )

        # expiring product
        self.expiring = Product.objects.create(
            item_name="Expiring",
            number=1,
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=1),
            description="exp",
            user=self.user,
            publish=True,
            valid=True,
            show_expiration_notice=True,
        )

    def test_product_str(self):
        self.assertIn("TestItem", str(self.product))

    def test_product_form_end_before_start_valid(self):
        data = {
            "item_name": "F1",
            "number": 1,
            "description": "d",
            "start_date": (date.today()).isoformat(),
            "start_clock": "00:00",
            "end_date": (date.today()).isoformat(),
            "end_clock": "23:59",
        }
        form = ProductForm(data=data)
        self.assertTrue(form.is_valid())

    def test_product_form_end_before_start_invalid(self):
        data = {
            "item_name": "F1",
            "number": 1,
            "description": "d",
            "start_date": (date.today()).isoformat(),
            "start_clock": "12:00",
            "end_date": (date.today()).isoformat(),
            "end_clock": "00:00",
        }
        form = ProductForm(data=data)
        self.assertFalse(form.is_valid())

    def test_get_expiring_products_includes_expiring(self):
        expiring = get_expiring_products()
        self.assertIn(self.expiring, list(expiring))


class ProductIntegrationTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.prod = User.objects.create_user(username="pv", password="pw", role="producer")
        now = timezone.now()
        self.p = Product.objects.create(item_name="I1", number=2, start_time=now, end_time=now + timedelta(days=1), description="d", user=self.prod, publish=True, valid=True)

    def test_consumer_product_list_access_by_role(self):
        # consumer should be allowed, producer should be redirected
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cons = User.objects.create_user(username="consx", password="pw", role="consumer")
        self.client.login(username="consx", password="pw")
        url = reverse("product:consumer_product_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        self.client.login(username="pv", password="pw")
        resp2 = self.client.get(url)
        self.assertNotEqual(resp2.status_code, 200)

    def test_product_application_model_create_and_str(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cons = User.objects.create_user(username="cons2", password="pw", role="consumer")
        app = ProductApplication.objects.create(product=self.p, user=cons, quantity=1, message="m")
        self.assertIn("Application", str(app))