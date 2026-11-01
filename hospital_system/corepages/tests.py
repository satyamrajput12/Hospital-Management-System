import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from corepages.models import ProductCategory, Product, Cart, CartItem, Order, OrderItem
from departments.models import Department, LabTest
from doctors.models import Doctor

User = get_user_model()


class CommerceAndSearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = ProductCategory.objects.create(name='Cardiology Meds', slug='cardiology-meds')
        
        self.product1 = Product.objects.create(
            name='Atorvastatin 20mg',
            slug='atorvastatin-20mg',
            category=self.category,
            price=Decimal('150.00'),
            discount_percent=20,
            stock=50,
            is_active=True
        )

        self.product2 = Product.objects.create(
            name='Metformin 500mg',
            slug='metformin-500mg',
            category=self.category,
            price=Decimal('80.00'),
            discount_percent=0,
            stock=10,
            is_active=True
        )

        self.user = User.objects.create_user(
            username='shopper_user',
            email='shopper@hospital.com',
            password='Password123!',
            first_name='Shopper',
            last_name='Patient',
            role=User.Role.PATIENT,
            is_email_verified=True,
            is_active=True
        )

        self.other_user = User.objects.create_user(
            username='intruder_user',
            email='intruder@hospital.com',
            password='Password123!',
            role=User.Role.PATIENT,
            is_email_verified=True,
            is_active=True
        )

        self.admin = User.objects.create_user(
            username='commerce_admin',
            email='admin_comm@hospital.com',
            password='Password123!',
            role=User.Role.ADMIN,
            is_staff=True,
            is_email_verified=True,
            is_active=True
        )

    def test_search_view_returns_matching_records(self):
        url = reverse('core:search')
        resp = self.client.get(url, {'q': 'Atorvastatin'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Atorvastatin 20mg')

    def test_backend_cart_api_operations(self):
        self.client.login(username='shopper_user', password='Password123!')
        
        # Add to cart via JSON API
        add_url = reverse('core:add_to_cart_api')
        resp = self.client.post(
            add_url,
            data=json.dumps({'product_id': self.product1.id, 'quantity': 2}),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['cart']['total_items'], 2)
        # 2 * 120.00 (discounted effective price) = 240.00
        self.assertEqual(data['cart']['subtotal'], 240.00)

        # Verify Cart in DB
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.total_items(), 2)
        self.assertEqual(cart.total_amount(), Decimal('240.00'))

    def test_checkout_decrements_inventory_safely(self):
        self.client.login(username='shopper_user', password='Password123!')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product1, quantity=3)

        initial_stock = self.product1.stock
        checkout_url = reverse('core:checkout')
        
        post_data = {
            'full_name': 'Shopper Patient',
            'email': 'shopper@hospital.com',
            'phone': '9876543210',
            'shipping_address': '742 Evergreen Terrace',
            'city': 'Springfield',
            'postal_code': '97477',
            'payment_method': 'COD',
            'notes': 'Leave at front door',
        }
        resp = self.client.post(checkout_url, post_data)
        self.assertEqual(resp.status_code, 302)

        # Inventory decremented
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, initial_stock - 3)

        # Order created: 3 * 120.00 = 360.00 + 40.00 shipping = 400.00
        order = Order.objects.get(patient=self.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.total_amount, Decimal('400.00'))
        self.assertEqual(order.payment_status, Order.PaymentStatus.COD)

    def test_cancel_order_restores_inventory(self):
        order = Order.objects.create(
            patient=self.user,
            order_number='ORD-TEST-999',
            full_name='Shopper Patient',
            email='shopper@hospital.com',
            phone='9876543210',
            shipping_address='742 Evergreen Terrace',
            total_amount=Decimal('240.00'),
            status=Order.Status.PENDING
        )
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            quantity=4,
            unit_price=Decimal('120.00'),
            subtotal=Decimal('480.00')
        )
        self.product1.stock = 40
        self.product1.save()

        self.client.login(username='shopper_user', password='Password123!')
        cancel_url = reverse('core:cancel_order', kwargs={'pk': order.id})

        # Reject GET
        resp_get = self.client.get(cancel_url)
        self.assertEqual(resp_get.status_code, 405)

        # Allow POST
        resp_post = self.client.post(cancel_url)
        self.assertRedirects(resp_post, reverse('core:my_orders'))

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)

        # Stock restored: 40 + 4 = 44
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 44)

    def test_order_idor_access_control(self):
        order = Order.objects.create(
            patient=self.user,
            order_number='ORD-PRIVATE-001',
            full_name='Shopper Patient',
            email='shopper@hospital.com',
            shipping_address='Confidential Address',
            total_amount=Decimal('120.00'),
            status=Order.Status.PENDING
        )

        detail_url = reverse('core:order_detail', kwargs={'pk': order.id})
        cancel_url = reverse('core:cancel_order', kwargs={'pk': order.id})

        # Intruder logged in
        self.client.login(username='intruder_user', password='Password123!')
        
        # Cannot view invoice/details
        resp1 = self.client.get(detail_url)
        self.assertEqual(resp1.status_code, 403)

        # Cannot cancel order
        resp2 = self.client.post(cancel_url)
        self.assertEqual(resp2.status_code, 403)

    def test_admin_product_management(self):
        self.client.login(username='commerce_admin', password='Password123!')
        toggle_url = reverse('core:admin_product_toggle', kwargs={'pk': self.product1.id})
        
        resp = self.client.post(toggle_url)
        self.assertRedirects(resp, reverse('core:admin_product_list'))
        self.product1.refresh_from_db()
        self.assertFalse(self.product1.is_active)
