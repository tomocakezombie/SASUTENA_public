from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

from django.contrib.auth import get_user_model
from .models import Product
from .forms import ProductForm
from adminPortal.models import ExpirationNoticeSetting


class ProductAppTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.producer = User.objects.create_user(username="prod", password="pw", role="producer")

	def test_product_str(self):
		p = Product.objects.create(item_name="トマト", number=1, start_time=timezone.now(), end_time=timezone.now()+timedelta(days=1), description="d", user=self.producer, publish=True, valid=True)
		self.assertIn("トマト", str(p))

	def test_productform_end_before_start_invalid(self):
		start = (timezone.now() + timedelta(days=2)).date()
		end = (timezone.now() + timedelta(days=1)).date()
		data = {
			"item_name": "x",
			"number": 1,
			"description": "d",
			"start_date": start.isoformat(),
			"end_date": end.isoformat(),
			"start_clock": "00:00",
			"end_clock": "00:00",
		}
		form = ProductForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertIn("end_date", form.errors)

	def test_get_expiring_products_respects_settings(self):
		notice = ExpirationNoticeSetting.objects.create(is_active=True, notify_days_before=2)
		now = timezone.now()
		p = Product.objects.create(item_name="soon", number=1, start_time=now, end_time=now + timedelta(days=1), description="d", user=self.producer, publish=True, valid=True, show_expiration_notice=True, completed=False)
		from .views import get_expiring_products
		qs = get_expiring_products()
		self.assertIn(p, list(qs))
