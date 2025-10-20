# # stock/tests.py
# from django.test import TestCase
# from rest_framework.test import APIClient
# from rest_framework import status
# from django.contrib.auth import get_user_model
# from .models import Product, Category

# User = get_user_model()

# class TransactionTests(TestCase):
#     def setUp(self):
#         self.client = APIClient()
#         # Create users: one manager and one cashier
#         self.manager = User.objects.create_user(username='manager', password='managerpass', role='manager')
#         self.cashier = User.objects.create_user(username='cashier', password='cashierpass', role='cashier')
#         # Create a category and product
#         self.category = Category.objects.create(name='Electronics')
#         self.product = Product.objects.create(name='Laptop', category=self.category, quantity=10, price=1000.00)

#     def authenticate(self, user):
#         response = self.client.post('/api/accounts/auth/jwt/create/', {'username': user.username, 'password': 'managerpass' if user.username == 'manager' else 'cashierpass'}, format='json')
#         token = response.data.get('access')
#         self.client.credentials(HTTP_AUTHORIZATION='JWT ' + token)

#     def test_non_manager_cannot_restock(self):
#         # Cashier should not be allowed to restock.
#         self.authenticate(self.cashier)
#         url = '/api/stock/restock/'
#         data = {'product': self.product.id, 'quantity': 5}
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

#     def test_sale_updates_product_quantity(self):
#         # A sale transaction should reduce product quantity.
#         self.authenticate(self.cashier)
#         url = '/api/stock/sales/'
#         data = {'product': self.product.id, 'quantity': 3}
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.product.refresh_from_db()
#         self.assertEqual(self.product.quantity, 10 - 3)

#     def test_restock_updates_product_quantity(self):
#         # A restock transaction should increase product quantity.
#         self.authenticate(self.manager)
#         url = '/api/stock/restock/'
#         data = {'product': self.product.id, 'quantity': 5}
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.product.refresh_from_db()
#         self.assertEqual(self.product.quantity, 10 + 5)

#     def test_insufficient_stock_for_sale(self):
#         # Trying to sell more than available should return an error.
#         self.authenticate(self.cashier)
#         url = '/api/stock/sales/'
#         data = {'product': self.product.id, 'quantity': 20}
#         response = self.client.post(url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn('Insufficient stock', response.data.get('detail', ''))

from django.test import TestCase, Client
from django.urls import reverse
from stock.models import Product, Transaction, Category
from accounts.models import CustomUser

class ManageBottleReturnsTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create test category
        self.category = Category.objects.create(name="Beverages")
        
        # Create test users
        self.manager = CustomUser.objects.create_user(
            username='manager',
            password='testpass',
            role='manager'
        )
        self.cashier = CustomUser.objects.create_user(
            username='cashier',
            password='testpass',
            role='cashier'
        )
        self.other_user = CustomUser.objects.create_user(
            username='other',
            password='testpass',
            role='other_role'
        )
        
        # Create a returnable product
        self.product = Product.objects.create(
            name='Pepsi',
            quantity=100,
            price=500,
            deposit_amount=200,
            is_returnable=True,
            bottles_outstanding=10
        )

    def test_access_permissions(self):
        # Manager should have access
        self.client.login(username='manager', password='testpass')
        response = self.client.get(reverse('manage_bottle_returns'))
        self.assertEqual(response.status_code, 200)
        
        # Cashier should have access
        self.client.login(username='cashier', password='testpass')
        response = self.client.get(reverse('manage_bottle_returns'))
        self.assertEqual(response.status_code, 200)
        
        # Other user should be redirected
        self.client.login(username='other', password='testpass')
        response = self.client.get(reverse('manage_bottle_returns'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('dashboard')))

    def test_get_request(self):
        self.client.login(username='cashier', password='testpass')
        response = self.client.get(reverse('manage_bottle_returns'))
        self.assertIn('form', response.context)
        self.assertIn('recent_returns', response.context)

    def test_valid_return(self):
        initial_outstanding = self.product.bottles_outstanding
        return_qty = 3
        
        self.client.login(username='cashier', password='testpass')
        response = self.client.post(reverse('manage_bottle_returns'), {
            'product': self.product.id,
            'quantity': return_qty
        }, follow=True)  # Follow redirect to see messages
        
        # Should redirect after successful return
        self.assertEqual(response.status_code, 200)
        
        # Verify product updated
        self.product.refresh_from_db()
        self.assertEqual(
            self.product.bottles_outstanding, 
            initial_outstanding - return_qty
        )
        
        # Verify transaction created
        refund_trans = Transaction.objects.filter(
            transaction_type='deposit_refund'
        ).first()
        self.assertIsNotNone(refund_trans)
        self.assertEqual(refund_trans.quantity, return_qty)
        self.assertEqual(refund_trans.amount, -return_qty * self.product.deposit_amount)
        
        # Verify success message
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn(f"Processed return of {return_qty} Pepsi", messages[0].message)

    def test_invalid_form(self):
        self.client.login(username='cashier', password='testpass')
        response = self.client.post(reverse('manage_bottle_returns'), {
            'product': self.product.id,
            'quantity': ''  # Invalid quantity
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_return_more_than_outstanding(self):
        # Try to return more than outstanding
        return_qty = self.product.bottles_outstanding + 5
        
        self.client.login(username='cashier', password='testpass')
        response = self.client.post(
            reverse('manage_bottle_returns'), 
            {
                'product': self.product.id,
                'quantity': return_qty
            },
            follow=True  # Follow redirect to see messages
        )
        
        # Should show error
        self.assertEqual(response.status_code, 200)
        
        # Product should not be updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.bottles_outstanding, 10)
        
        # Error message should be shown
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn("Cannot return", messages[0].message)
        self.assertIn("outstanding", messages[0].message)

    def test_non_returnable_product(self):
        # Create non-returnable product
        non_returnable = Product.objects.create(
            name='Chips',
            quantity=50,
            price=300,
            deposit_amount=0,
            is_returnable=False
        )
        
        self.client.login(username='cashier', password='testpass')
        response = self.client.post(
            reverse('manage_bottle_returns'), 
            {
                'product': non_returnable.id,
                'quantity': 2
            },
            follow=True  # Follow redirect to see messages
        )
        
        # Should show error
        self.assertEqual(response.status_code, 200)
        
        # Error message should be shown
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn("is not a returnable product", messages[0].message)

    def test_recent_returns_context(self):
        # Create some returns
        for i in range(1, 6):
            Transaction.objects.create(
                product=self.product,
                quantity=i,
                transaction_type='deposit_refund',
                created_by=self.cashier,
                amount=-i * 200
            )
        
        self.client.login(username='cashier', password='testpass')
        response = self.client.get(reverse('manage_bottle_returns'))
        
        # Should show most recent 20 returns
        recent_returns = response.context['recent_returns']
        self.assertEqual(len(recent_returns), 5)
        self.assertEqual(recent_returns[0].quantity, 5)  # Most recent first