import uuid

from django.db import models
from django.utils import timezone

# =========================================================
# PRODUCT
# =========================================================


class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    image = models.URLField(blank=True)
    category = models.CharField(max_length=100)

    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# =========================================================
# REVIEW
# =========================================================


class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()

    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.rating}/5"


# =========================================================
# CART
# =========================================================


class Cart(models.Model):
    session_key = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.session_key}"


# =========================================================
# CART ITEM
# =========================================================


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(default=1)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity


# =========================================================
# COUPON
# =========================================================


class Coupon(models.Model):

    DISCOUNT_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]

    code = models.CharField(max_length=50, unique=True)

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_CHOICES,
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    maximum_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    usage_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


# =========================================================
# ORDER
# =========================================================


class Order(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("online", "Online Payment"),
    ]

    order_number = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    session_key = models.CharField(max_length=100)
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_orders",
    )

    customer_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    shipping_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    coupon = models.ForeignKey(
        "Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="cod",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default="pending",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.order_number}"


# =========================================================
# ORDER ITEM
# =========================================================


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    product_name = models.CharField(max_length=255)
    product_image = models.URLField(blank=True)

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity


# =========================================================
# WISHLIST ITEM
# =========================================================


class WishlistItem(models.Model):

    session_key = models.CharField(max_length=100)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session_key", "product"],
                name="unique_session_wishlist_product",
            )
        ]

    def __str__(self):
        return f"Wishlist - {self.product.name}"
