from django.test import TestCase
from api.models import Product
from django.db import IntegrityError, transaction
from api.models import Cart, CartItem
from api.models import Coupon
from django.contrib.auth.models import User
from api.models import Order
from api.models import OrderItem
from api.models import Product, Review, Order, WishlistItem


class CustomerMyOrdersTest(TestCase):

    # Helper: Create a test order
    def create_order(self, user, session_key):
        return Order.objects.create(
            user=user,
            session_key=session_key,
            customer_name="Test Customer",
            email="test@example.com",
            phone="9999999999",
            shipping_address="Test Address",
            city="Bhubaneswar",
            state="Odisha",
            postal_code="751001",
            subtotal=1000,
            total_amount=1000,
        )

    # Test 1: POST request should be rejected
    def test_my_orders_rejects_post(self):
        response = self.client.post("/api/auth/my-orders/")

        self.assertEqual(response.status_code, 405)
        self.assertFalse(response.json()["success"])

    # Test 2: Login is required
    def test_my_orders_requires_login(self):
        response = self.client.get("/api/auth/my-orders/")

        self.assertEqual(response.status_code, 401)

    # Test 3: Logged-in user can access My Orders
    def test_logged_in_user_can_access_my_orders(self):
        User.objects.create_user(
            username="orders_test_user", password="TestPassword123!"
        )

        self.client.login(username="orders_test_user", password="TestPassword123!")

        response = self.client.get("/api/auth/my-orders/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["count"], 0)

    # Test 4: Order user field must be nullable
    def test_order_user_field_is_nullable(self):
        user_field = Order._meta.get_field("user")

        self.assertTrue(user_field.null)
        self.assertTrue(user_field.blank)

    # Test 5: User can only see their own orders
    def test_user_only_sees_their_own_orders(self):
        user1 = User.objects.create_user(
            username="customer_one", password="TestPassword123!"
        )

        user2 = User.objects.create_user(
            username="customer_two", password="TestPassword123!"
        )

        order1 = self.create_order(user1, "test_session_one")

        order2 = self.create_order(user2, "test_session_two")

        self.client.login(username="customer_one", password="TestPassword123!")

        response = self.client.get("/api/auth/my-orders/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

        returned_orders = response.json()["orders"]

        # Verify correct order is returned
        self.assertEqual(returned_orders[0]["order_number"], str(order1.order_number))

        # Verify other customer's order is not returned
        self.assertNotEqual(
            returned_orders[0]["order_number"], str(order2.order_number)
        )

        # Verify response fields
        order_data = returned_orders[0]

        required_fields = [
            "order_number",
            "status",
            "payment_method",
            "payment_status",
            "subtotal",
            "discount_amount",
            "shipping_cost",
            "total_amount",
            "created_at",
            "items",
        ]

        for field in required_fields:
            self.assertIn(field, order_data)


from django.db import IntegrityError, transaction
from api.models import Product, WishlistItem


class WishlistModelTest(TestCase):

    def test_duplicate_wishlist_product_is_rejected(self):
        product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=100,
            category="Electronics",
            stock=10,
        )

        WishlistItem.objects.create(
            session_key="wishlist_test_session",
            product=product,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WishlistItem.objects.create(
                    session_key="wishlist_test_session",
                    product=product,
                )


class ProductModelTest(TestCase):

    def test_product_default_values(self):
        product = Product.objects.create(
            name="Validation Test Product",
            slug="validation-test-product",
            price=500,
            category="Electronics",
        )

        self.assertEqual(product.stock, 0)
        self.assertTrue(product.is_active)
        self.assertFalse(product.is_featured)

    def test_product_price_and_stock_values(self):
        product = Product.objects.create(
            name="Price Test Product",
            slug="price-test-product",
            price=999.99,
            category="Electronics",
            stock=25,
        )

        self.assertEqual(product.price, 999.99)
        self.assertEqual(product.stock, 25)


class ReviewModelTest(TestCase):

    def test_review_is_unapproved_by_default(self):
        product = Product.objects.create(
            name="Review Test Product",
            slug="review-test-product",
            price=500,
            category="Electronics",
        )

        review = Review.objects.create(
            product=product,
            name="Test Customer",
            rating=5,
            comment="Excellent product!",
        )

        self.assertFalse(review.is_approved)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.product, product)


class CouponModelTest(TestCase):

    def test_coupon_default_values(self):
        coupon = Coupon.objects.create(
            code="TEST100",
            discount_type="percentage",
            discount_value=10,
        )

        self.assertTrue(coupon.is_active)
        self.assertEqual(coupon.usage_count, 0)
        self.assertEqual(coupon.minimum_order_amount, 0)

    def test_coupon_code_must_be_unique(self):
        Coupon.objects.create(
            code="UNIQUE100",
            discount_type="fixed",
            discount_value=100,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Coupon.objects.create(
                    code="UNIQUE100",
                    discount_type="fixed",
                    discount_value=200,
                )


class OrderItemModelTest(TestCase):

    def test_order_item_total_price(self):
        order = Order.objects.create(
            session_key="orderitem_test_session",
            customer_name="Test Customer",
            email="test@example.com",
            phone="9999999999",
            shipping_address="Test Address",
            city="Bhubaneswar",
            state="Odisha",
            postal_code="751001",
            subtotal=2000,
            total_amount=2000,
        )

        item = OrderItem.objects.create(
            order=order,
            product_name="Test Item",
            quantity=3,
            unit_price=500,
        )

        self.assertEqual(item.total_price, 1500)


class CartItemModelTest(TestCase):

    def test_cart_item_total_price(self):
        product = Product.objects.create(
            name="Cart Test Product",
            slug="cart-test-product",
            price=500,
            category="Electronics",
            stock=10,
        )

        cart = Cart.objects.create(
            session_key="cartitem_test_session",
        )

        item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=3,
            unit_price=500,
        )

        self.assertEqual(item.total_price, 1500)

    def test_duplicate_product_in_same_cart_is_rejected(self):
        product = Product.objects.create(
            name="Duplicate Cart Product",
            slug="duplicate-cart-product",
            price=100,
            category="Electronics",
            stock=10,
        )

        cart = Cart.objects.create(
            session_key="duplicate_cart_session",
        )

        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=1,
            unit_price=100,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=2,
                    unit_price=100,
                )


class OrderModelDefaultsTest(TestCase):

    def test_order_default_status_and_payment(self):
        order = Order.objects.create(
            session_key="order_defaults_test",
            customer_name="Test Customer",
            email="test@example.com",
            phone="9999999999",
            shipping_address="Test Address",
            city="Bhubaneswar",
            state="Odisha",
            postal_code="751001",
            subtotal=500,
            total_amount=500,
        )

        self.assertEqual(order.status, "pending")
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.payment_method, "cod")
        self.assertEqual(order.country, "India")
        self.assertEqual(order.discount_amount, 0)
        self.assertEqual(order.shipping_cost, 0)
