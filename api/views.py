from decimal import Decimal
import json
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from django.db import transaction
from django.db.models import Q, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Product,
    Review,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Coupon,
    WishlistItem,
)

# =========================================================
# HELPERS
# =========================================================


def product_data(product, include_description=True):
    data = {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "price": str(product.price),
        "original_price": (
            str(product.original_price) if product.original_price is not None else None
        ),
        "image": product.image,
        "category": product.category,
        "stock": product.stock,
    }

    if include_description:
        data["description"] = product.description

    return data


def order_items_data(order):
    return [
        {
            "product_id": item.product_id,
            "product_name": item.product_name,
            "product_image": item.product_image,
            "quantity": item.quantity,
            "unit_price": str(item.unit_price),
            "item_total": str(item.total_price),
        }
        for item in order.items.all()
    ]


def order_data(order):
    return {
        "id": order.id,
        "order_number": str(order.order_number),
        "customer_name": order.customer_name,
        "email": order.email,
        "phone": order.phone,
        "shipping_address": order.shipping_address,
        "city": order.city,
        "state": order.state,
        "postal_code": order.postal_code,
        "country": order.country,
        "subtotal": str(order.subtotal),
        "discount_amount": str(order.discount_amount),
        "coupon_code": order.coupon.code if order.coupon else None,
        "shipping_cost": str(order.shipping_cost),
        "total_amount": str(order.total_amount),
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "status": order.status,
        "notes": order.notes,
        "items": order_items_data(order),
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }


def json_body(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(body, dict):
        return None

    return body


# =========================================================
# API HOME
# =========================================================


def api_home(request):
    return JsonResponse(
        {
            "status": "success",
            "message": "ShopEase API is running",
            "project": "ShopEase",
            "version": "1.0",
        }
    )


# =========================================================
# PRODUCTS
# =========================================================


def products_list(request):
    products = Product.objects.filter(is_active=True)

    data = [product_data(p) for p in products]

    return JsonResponse(
        {
            "status": "success",
            "count": len(data),
            "products": data,
        }
    )


def categories_list(request):
    categories = (
        Product.objects.filter(is_active=True)
        .values_list("category", flat=True)
        .distinct()
    )

    data = list(categories)

    return JsonResponse(
        {
            "status": "success",
            "count": len(data),
            "categories": data,
        }
    )


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    return JsonResponse(
        {
            "status": "success",
            "product": product_data(product),
        }
    )


def product_search(request):
    query = request.GET.get("q", "").strip()

    products = Product.objects.filter(is_active=True)

    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__icontains=query)
        )

    data = [product_data(p) for p in products]

    return JsonResponse(
        {
            "status": "success",
            "query": query,
            "count": len(data),
            "products": data,
        }
    )


def product_filter(request):
    products = Product.objects.filter(is_active=True)

    category = request.GET.get("category")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    if category:
        products = products.filter(category__iexact=category)

    if min_price:
        products = products.filter(price__gte=min_price)

    if max_price:
        products = products.filter(price__lte=max_price)

    data = [product_data(p, include_description=False) for p in products]

    return JsonResponse(
        {
            "status": "success",
            "count": len(data),
            "products": data,
        }
    )


def product_sort(request):
    products = Product.objects.filter(is_active=True)

    sort_by = request.GET.get("sort", "newest")

    if sort_by == "price_low":
        products = products.order_by("price")
    elif sort_by == "price_high":
        products = products.order_by("-price")
    elif sort_by == "name":
        products = products.order_by("name")
    else:
        products = products.order_by("-created_at")

    data = [product_data(p, include_description=False) for p in products]

    return JsonResponse(
        {
            "status": "success",
            "sort": sort_by,
            "count": len(data),
            "products": data,
        }
    )


def product_pagination(request):
    products = Product.objects.filter(is_active=True)

    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 10)

    try:
        per_page = int(per_page)
        if per_page < 1 or per_page > 100:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10

    paginator = Paginator(products, per_page)
    page_obj = paginator.get_page(page_number)

    data = [product_data(p, include_description=False) for p in page_obj]

    return JsonResponse(
        {
            "status": "success",
            "total_products": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "per_page": per_page,
            "products": data,
        }
    )


def product_stock_status(request):
    products = Product.objects.filter(is_active=True)

    data = []

    for product in products:
        if product.stock == 0:
            status = "out_of_stock"
        elif product.stock <= 5:
            status = "low_stock"
        else:
            status = "in_stock"

        data.append(
            {
                "id": product.id,
                "name": product.name,
                "stock": product.stock,
                "stock_status": status,
            }
        )

    return JsonResponse(
        {
            "status": "success",
            "products": data,
        }
    )


def featured_products(request):
    products = Product.objects.filter(
        is_active=True,
        is_featured=True,
    )

    data = [product_data(p, include_description=False) for p in products]

    return JsonResponse(
        {
            "status": "success",
            "count": len(data),
            "products": data,
        }
    )


# =========================================================
# REVIEWS
# =========================================================


def product_reviews(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    reviews = Review.objects.filter(
        product=product,
        is_approved=True,
    ).order_by("-created_at")

    average_rating = reviews.aggregate(average=Avg("rating"))["average"]

    data = [
        {
            "id": review.id,
            "name": review.name,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at.isoformat(),
        }
        for review in reviews
    ]

    return JsonResponse(
        {
            "status": "success",
            "product": product.name,
            "total_reviews": len(data),
            "average_rating": round(average_rating, 1) if average_rating else 0,
            "reviews": data,
        }
    )


@csrf_exempt
def submit_product_review(request, product_id):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    product = get_object_or_404(Product, id=product_id, is_active=True)

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    name = str(body.get("name", "")).strip()
    comment = str(body.get("comment", "")).strip()

    try:
        rating = int(body.get("rating", 0))
    except (ValueError, TypeError, OverflowError):
        rating = 0

    if not name or not comment:
        return JsonResponse(
            {
                "status": "error",
                "message": "Name and comment are required.",
            },
            status=400,
        )

    if len(name) > 100:
        return JsonResponse(
            {
                "status": "error",
                "message": "Name cannot exceed 100 characters.",
            },
            status=400,
        )

    if len(comment) > 2000:
        return JsonResponse(
            {
                "status": "error",
                "message": "Comment cannot exceed 2000 characters.",
            },
            status=400,
        )

    if rating < 1 or rating > 5:
        return JsonResponse(
            {
                "status": "error",
                "message": "Rating must be between 1 and 5.",
            },
            status=400,
        )

    review = Review.objects.create(
        product=product,
        name=name,
        rating=rating,
        comment=comment,
        is_approved=False,
    )

    return JsonResponse(
        {
            "status": "success",
            "message": "Review submitted successfully. Awaiting admin approval.",
            "review_id": review.id,
            "is_approved": review.is_approved,
        },
        status=201,
    )


# =========================================================
# CART
# =========================================================


@csrf_exempt
def add_to_cart(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    session_key = str(body.get("session_key", "")).strip()
    product_id = body.get("product_id")
    quantity = body.get("quantity", 1)

    if not session_key:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key is required.",
            },
            status=400,
        )

    if len(session_key) > 100:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key is too long.",
            },
            status=400,
        )

    if product_id is None or product_id == "":
        return JsonResponse(
            {
                "status": "error",
                "message": "Product ID is required.",
            },
            status=400,
        )

    try:
        product_id = int(product_id)
        quantity = int(quantity)
    except (ValueError, TypeError, OverflowError):
        return JsonResponse(
            {
                "status": "error",
                "message": "Product ID and quantity must be valid integers.",
            },
            status=400,
        )

    if product_id < 1 or quantity < 1:
        return JsonResponse(
            {
                "status": "error",
                "message": "Product ID and quantity must be positive.",
            },
            status=400,
        )

    product = Product.objects.filter(
        id=product_id,
        is_active=True,
    ).first()

    if not product:
        return JsonResponse(
            {
                "status": "error",
                "message": "Product not found.",
            },
            status=404,
        )

    if product.stock < 1:
        return JsonResponse(
            {
                "status": "error",
                "message": "Product is out of stock.",
            },
            status=400,
        )

    cart, _ = Cart.objects.get_or_create(session_key=session_key)

    cart_item = CartItem.objects.filter(
        cart=cart,
        product=product,
    ).first()

    new_quantity = quantity

    if cart_item:
        new_quantity += cart_item.quantity

    if new_quantity > product.stock:
        return JsonResponse(
            {
                "status": "error",
                "message": "Requested quantity exceeds available stock.",
                "available_stock": product.stock,
            },
            status=400,
        )

    if cart_item:
        cart_item.quantity = new_quantity
        cart_item.unit_price = product.price
        cart_item.save()
    else:
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            unit_price=product.price,
        )

    return JsonResponse(
        {
            "status": "success",
            "message": "Product added to cart successfully.",
            "cart_id": cart.id,
            "item_id": cart_item.id,
            "product": product.name,
            "quantity": cart_item.quantity,
            "unit_price": str(cart_item.unit_price),
            "item_total": str(cart_item.total_price),
        },
        status=201,
    )


def view_cart(request):
    session_key = request.GET.get("session_key", "").strip()

    if not session_key:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key is required.",
            },
            status=400,
        )

    cart = Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return JsonResponse(
            {
                "status": "success",
                "message": "Cart is empty.",
                "items": [],
                "total_items": 0,
                "cart_total": "0.00",
            }
        )

    cart_items = cart.items.select_related("product").all()

    items = []
    cart_total = Decimal("0.00")
    total_items = 0

    for item in cart_items:
        items.append(
            {
                "item_id": item.id,
                "product_id": item.product.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "item_total": str(item.total_price),
            }
        )

        cart_total += item.total_price
        total_items += item.quantity

    return JsonResponse(
        {
            "status": "success",
            "cart_id": cart.id,
            "total_items": total_items,
            "cart_total": str(cart_total),
            "items": items,
        }
    )


@csrf_exempt
def update_cart_item(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    session_key = str(body.get("session_key", "")).strip()
    item_id = body.get("item_id")
    quantity = body.get("quantity")

    if not session_key or item_id is None or quantity is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key, item ID and quantity are required.",
            },
            status=400,
        )

    try:
        item_id = int(item_id)
        quantity = int(quantity)
    except (ValueError, TypeError, OverflowError):
        return JsonResponse(
            {
                "status": "error",
                "message": "Item ID and quantity must be valid integers.",
            },
            status=400,
        )

    if len(session_key) > 100 or item_id < 1 or quantity < 1:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid cart input.",
            },
            status=400,
        )

    cart = Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return JsonResponse(
            {
                "status": "error",
                "message": "Cart not found.",
            },
            status=404,
        )

    cart_item = cart.items.select_related("product").filter(id=item_id).first()

    if not cart_item:
        return JsonResponse(
            {
                "status": "error",
                "message": "Cart item not found.",
            },
            status=404,
        )

    product = cart_item.product

    if not product.is_active:
        return JsonResponse(
            {
                "status": "error",
                "message": "This product is no longer available.",
            },
            status=400,
        )

    if quantity > product.stock:
        return JsonResponse(
            {
                "status": "error",
                "message": "Requested quantity exceeds available stock.",
                "available_stock": product.stock,
            },
            status=400,
        )

    cart_item.quantity = quantity
    cart_item.unit_price = product.price
    cart_item.save()

    return JsonResponse(
        {
            "status": "success",
            "message": "Cart item quantity updated successfully.",
            "cart_id": cart.id,
            "item_id": cart_item.id,
            "product": product.name,
            "quantity": quantity,
            "unit_price": str(cart_item.unit_price),
            "item_total": str(cart_item.total_price),
        }
    )


@csrf_exempt
def remove_cart_item(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    session_key = str(body.get("session_key", "")).strip()
    item_id = body.get("item_id")

    if not session_key or item_id is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key and item ID are required.",
            },
            status=400,
        )

    try:
        item_id = int(item_id)
    except (ValueError, TypeError, OverflowError):
        return JsonResponse(
            {
                "status": "error",
                "message": "Item ID must be a valid integer.",
            },
            status=400,
        )

    if len(session_key) > 100 or item_id < 1:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid input.",
            },
            status=400,
        )

    cart = Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return JsonResponse(
            {
                "status": "error",
                "message": "Cart not found.",
            },
            status=404,
        )

    cart_item = cart.items.select_related("product").filter(id=item_id).first()

    if not cart_item:
        return JsonResponse(
            {
                "status": "error",
                "message": "Cart item not found.",
            },
            status=404,
        )

    product_name = cart_item.product.name
    cart_item.delete()

    return JsonResponse(
        {
            "status": "success",
            "message": "Cart item removed successfully.",
            "cart_id": cart.id,
            "removed_item_id": item_id,
            "removed_product": product_name,
        }
    )


@csrf_exempt
def clear_cart(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    session_key = str(body.get("session_key", "")).strip()

    if not session_key or len(session_key) > 100:
        return JsonResponse(
            {
                "status": "error",
                "message": "Valid session key is required.",
            },
            status=400,
        )

    cart = Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return JsonResponse(
            {
                "status": "error",
                "message": "Cart not found.",
            },
            status=404,
        )

    deleted_count, _ = cart.items.all().delete()

    return JsonResponse(
        {
            "status": "success",
            "message": "Cart cleared successfully.",
            "cart_id": cart.id,
            "removed_items": deleted_count,
            "total_items": 0,
            "cart_total": "0.00",
        }
    )


# =========================================================
# CHECKOUT
# =========================================================


@csrf_exempt
def checkout(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    session_key = str(body.get("session_key", "")).strip()

    if not session_key or len(session_key) > 100:
        return JsonResponse(
            {
                "status": "error",
                "message": "Valid session key is required.",
            },
            status=400,
        )

    # Required customer and shipping fields
    required_fields = [
        "customer_name",
        "email",
        "phone",
        "shipping_address",
        "city",
        "state",
        "postal_code",
    ]

    for field in required_fields:
        if not str(body.get(field, "")).strip():
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"{field.replace('_', ' ').title()} is required.",
                },
                status=400,
            )

    customer_name = str(body["customer_name"]).strip()
    email = str(body["email"]).strip()
    phone = str(body["phone"]).strip()
    shipping_address = str(body["shipping_address"]).strip()
    city = str(body["city"]).strip()
    state = str(body["state"]).strip()
    postal_code = str(body["postal_code"]).strip()
    country = str(body.get("country", "India")).strip() or "India"
    notes = str(body.get("notes", "")).strip()
    coupon_code = str(body.get("coupon_code", "")).strip().upper()

    if len(customer_name) > 255:
        return JsonResponse(
            {
                "status": "error",
                "message": "Customer name is too long.",
            },
            status=400,
        )

    if len(email) > 254:
        return JsonResponse(
            {
                "status": "error",
                "message": "Email is too long.",
            },
            status=400,
        )

    if len(phone) > 20:
        return JsonResponse(
            {
                "status": "error",
                "message": "Phone number is too long.",
            },
            status=400,
        )

    if len(shipping_address) > 500:
        return JsonResponse(
            {
                "status": "error",
                "message": "Shipping address is too long.",
            },
            status=400,
        )

    if len(city) > 100 or len(state) > 100:
        return JsonResponse(
            {
                "status": "error",
                "message": "City or state name is too long.",
            },
            status=400,
        )

    if len(postal_code) > 20 or len(country) > 100:
        return JsonResponse(
            {
                "status": "error",
                "message": "Postal code or country is too long.",
            },
            status=400,
        )

    if len(notes) > 1000:
        return JsonResponse(
            {
                "status": "error",
                "message": "Notes cannot exceed 1000 characters.",
            },
            status=400,
        )

    # COD only for now
    payment_method = str(body.get("payment_method", "cod")).strip().lower()

    if payment_method != "cod":
        return JsonResponse(
            {
                "status": "error",
                "message": "Currently only Cash on Delivery is supported.",
            },
            status=400,
        )

    try:
        with transaction.atomic():

            # Lock cart
            cart = (
                Cart.objects.select_for_update().filter(session_key=session_key).first()
            )

            if not cart:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Cart not found.",
                    },
                    status=404,
                )

            cart_items = list(cart.items.select_related("product").all())

            if not cart_items:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Your cart is empty.",
                    },
                    status=400,
                )

            # Lock product rows to prevent concurrent stock changes
            product_ids = [item.product_id for item in cart_items]

            locked_products = {
                product.id: product
                for product in Product.objects.select_for_update().filter(
                    id__in=product_ids
                )
            }

            subtotal = Decimal("0.00")

            # Validate stock and product availability
            for item in cart_items:
                product = locked_products.get(item.product_id)

                if not product or not product.is_active:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": f"{item.product_name if hasattr(item, 'product_name') else item.product.name} is unavailable.",
                        },
                        status=400,
                    )

                if item.quantity < 1 or item.quantity > product.stock:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": f"Insufficient stock for {product.name}.",
                            "available_stock": product.stock,
                        },
                        status=400,
                    )

                subtotal += item.unit_price * item.quantity

            subtotal = subtotal.quantize(Decimal("0.01"))

            # Validate coupon
            coupon = None
            discount_amount = Decimal("0.00")

            if coupon_code:
                coupon = (
                    Coupon.objects.select_for_update()
                    .filter(code__iexact=coupon_code)
                    .first()
                )

                if not coupon:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Invalid coupon code.",
                        },
                        status=400,
                    )

                now = timezone.now()

                if not coupon.is_active:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "This coupon is inactive.",
                        },
                        status=400,
                    )

                if coupon.valid_from and coupon.valid_from > now:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "This coupon is not yet valid.",
                        },
                        status=400,
                    )

                if coupon.valid_until and coupon.valid_until < now:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "This coupon has expired.",
                        },
                        status=400,
                    )

                if (
                    coupon.usage_limit is not None
                    and coupon.usage_count >= coupon.usage_limit
                ):
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Coupon usage limit has been reached.",
                        },
                        status=400,
                    )

                if subtotal < coupon.minimum_order_amount:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Minimum order amount for this coupon is not met.",
                            "minimum_order_amount": str(coupon.minimum_order_amount),
                        },
                        status=400,
                    )

                if coupon.discount_type == "percentage":
                    discount_amount = subtotal * coupon.discount_value / Decimal("100")
                elif coupon.discount_type == "fixed":
                    discount_amount = coupon.discount_value
                else:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Invalid coupon discount type.",
                        },
                        status=400,
                    )

                if coupon.maximum_discount is not None:
                    discount_amount = min(
                        discount_amount,
                        coupon.maximum_discount,
                    )

                discount_amount = min(
                    discount_amount,
                    subtotal,
                ).quantize(Decimal("0.01"))

            # Shipping currently free
            shipping_cost = Decimal("0.00")

            total_amount = (subtotal - discount_amount + shipping_cost).quantize(
                Decimal("0.01")
            )

            # Create order
            order = Order.objects.create(
                session_key=session_key,
                user=request.user if request.user.is_authenticated else None,
                customer_name=customer_name,
                email=email,
                phone=phone,
                shipping_address=shipping_address,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                subtotal=subtotal,
                discount_amount=discount_amount,
                coupon=coupon,
                shipping_cost=shipping_cost,
                total_amount=total_amount,
                payment_method="cod",
                payment_status="pending",
                status="pending",
                notes=notes,
            )

            # Create order items and decrease stock
            for item in cart_items:
                product = locked_products[item.product_id]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_image=product.image or "",
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )

                product.stock -= item.quantity
                product.save(update_fields=["stock"])

            # Increase coupon usage count
            if coupon:
                coupon.usage_count += 1
                coupon.save(update_fields=["usage_count"])

            # Clear cart only after successful order creation
            cart.items.all().delete()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Order placed successfully.",
                    "order": order_data(order),
                },
                status=201,
            )

    except Exception as e:
        return JsonResponse(
            {
                "status": "error",
                "message": "Unable to place order.",
                "detail": str(e),
            },
            status=500,
        )


# =========================================================
# ORDER HISTORY
# =========================================================


def order_history(request):
    session_key = request.GET.get("session_key", "").strip()

    if not session_key:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key is required.",
            },
            status=400,
        )

    orders = Order.objects.filter(session_key=session_key).order_by("-created_at")

    data = [order_data(order) for order in orders]

    return JsonResponse(
        {
            "status": "success",
            "count": len(data),
            "orders": data,
        }
    )


# =========================================================
# ORDER DETAIL
# =========================================================


def order_detail(request, order_id):
    session_key = request.GET.get("session_key", "").strip()

    if not session_key:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key is required.",
            },
            status=400,
        )

    order = Order.objects.filter(
        id=order_id,
        session_key=session_key,
    ).first()

    if not order:
        return JsonResponse(
            {
                "status": "error",
                "message": "Order not found.",
            },
            status=404,
        )

    return JsonResponse(
        {
            "status": "success",
            "order": order_data(order),
        }
    )


# =========================================================
# CANCEL ORDER
# =========================================================


@csrf_exempt
def cancel_order(request, order_id):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    session_key = str(body.get("session_key", "")).strip()

    if not session_key:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key is required.",
            },
            status=400,
        )

    try:
        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .filter(
                    id=order_id,
                    session_key=session_key,
                )
                .first()
            )

            if not order:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Order not found.",
                    },
                    status=404,
                )

            if order.status not in ["pending", "confirmed"]:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "This order cannot be cancelled.",
                        "current_status": order.status,
                    },
                    status=400,
                )

            order_items = list(order.items.all())

            products = {
                product.id: product
                for product in Product.objects.select_for_update().filter(
                    id__in=[item.product_id for item in order_items]
                )
            }

            # Restore product stock
            for item in order_items:
                product = products.get(item.product_id)

                if product:
                    product.stock += item.quantity
                    product.save(update_fields=["stock"])

            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Order cancelled successfully.",
                    "order": order_data(order),
                }
            )

    except Exception as e:
        return JsonResponse(
            {
                "status": "error",
                "message": "Unable to cancel order.",
                "detail": str(e),
            },
            status=500,
        )


# =========================================================
# COUPON VALIDATION
# =========================================================


@csrf_exempt
def validate_coupon(request):
    if request.method != "POST":
        return JsonResponse(
            {
                "status": "error",
                "message": "Only POST method is allowed.",
            },
            status=405,
        )

    body = json_body(request)

    if body is None:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid JSON data.",
            },
            status=400,
        )

    session_key = str(body.get("session_key", "")).strip()
    code = str(body.get("code", body.get("coupon_code", ""))).strip().upper()

    if not session_key or not code:
        return JsonResponse(
            {
                "status": "error",
                "message": "Session key and coupon code are required.",
            },
            status=400,
        )

    cart = Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return JsonResponse(
            {
                "status": "error",
                "message": "Cart not found.",
            },
            status=404,
        )

    cart_items = cart.items.select_related("product").all()

    if not cart_items.exists():
        return JsonResponse(
            {
                "status": "error",
                "message": "Cart is empty.",
            },
            status=400,
        )

    subtotal = sum(
        (item.total_price for item in cart_items),
        Decimal("0.00"),
    )

    coupon = Coupon.objects.filter(code__iexact=code).first()

    if not coupon:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid coupon code.",
            },
            status=400,
        )

    now = timezone.now()

    if not coupon.is_active:
        return JsonResponse(
            {
                "status": "error",
                "message": "Coupon is inactive.",
            },
            status=400,
        )

    if coupon.valid_from and coupon.valid_from > now:
        return JsonResponse(
            {
                "status": "error",
                "message": "Coupon is not yet valid.",
            },
            status=400,
        )

    if coupon.valid_until and coupon.valid_until < now:
        return JsonResponse(
            {
                "status": "error",
                "message": "Coupon has expired.",
            },
            status=400,
        )

    if coupon.usage_limit is not None and coupon.usage_count >= coupon.usage_limit:
        return JsonResponse(
            {
                "status": "error",
                "message": "Coupon usage limit reached.",
            },
            status=400,
        )

    if subtotal < coupon.minimum_order_amount:
        return JsonResponse(
            {
                "status": "error",
                "message": "Minimum order amount not met.",
                "minimum_order_amount": str(coupon.minimum_order_amount),
            },
            status=400,
        )

    if coupon.discount_type == "percentage":
        discount = subtotal * coupon.discount_value / Decimal("100")
    elif coupon.discount_type == "fixed":
        discount = coupon.discount_value
    else:
        return JsonResponse(
            {
                "status": "error",
                "message": "Invalid coupon discount type.",
            },
            status=400,
        )

    if coupon.maximum_discount is not None:
        discount = min(discount, coupon.maximum_discount)

    discount = min(discount, subtotal).quantize(Decimal("0.01"))

    return JsonResponse(
        {
            "status": "success",
            "message": "Coupon applied successfully.",
            "coupon_code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": str(coupon.discount_value),
            "subtotal": str(subtotal),
            "discount_amount": str(discount),
            "total_after_discount": str(subtotal - discount),
        }
    )


# =========================================================
# WISHLIST API
# =========================================================


@csrf_exempt
def wishlist_view(request):

    if request.method != "GET":
        return JsonResponse(
            {"success": False, "message": "GET method required."},
            status=405,
        )

    session_key = request.GET.get("session_key")

    if not session_key:
        return JsonResponse(
            {"success": False, "message": "Session key is required."},
            status=400,
        )

    items = WishlistItem.objects.filter(session_key=session_key).select_related(
        "product"
    )

    wishlist = [
        {
            "id": item.id,
            "product": product_data(
                item.product,
                include_description=False,
            ),
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]

    return JsonResponse(
        {
            "success": True,
            "count": len(wishlist),
            "wishlist": wishlist,
        }
    )


@csrf_exempt
def wishlist_add(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    data = json_body(request)

    if data is None:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400,
        )

    session_key = data.get("session_key")
    product_id = data.get("product_id")

    if not session_key or not product_id:
        return JsonResponse(
            {
                "success": False,
                "message": "Session key and product ID are required.",
            },
            status=400,
        )

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return JsonResponse(
            {"success": False, "message": "Invalid product ID."},
            status=400,
        )

    product = Product.objects.filter(
        id=product_id,
        is_active=True,
    ).first()

    if not product:
        return JsonResponse(
            {"success": False, "message": "Product not found."},
            status=404,
        )

    item, created = WishlistItem.objects.get_or_create(
        session_key=session_key,
        product=product,
    )

    return JsonResponse(
        {
            "success": True,
            "message": (
                "Product added to wishlist."
                if created
                else "Product already in wishlist."
            ),
            "created": created,
            "item": {
                "id": item.id,
                "product": product_data(
                    product,
                    include_description=False,
                ),
            },
        },
        status=201 if created else 200,
    )


@csrf_exempt
def wishlist_remove(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    data = json_body(request)

    if data is None:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400,
        )

    session_key = data.get("session_key")
    product_id = data.get("product_id")

    if not session_key or not product_id:
        return JsonResponse(
            {
                "success": False,
                "message": "Session key and product ID are required.",
            },
            status=400,
        )

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return JsonResponse(
            {"success": False, "message": "Invalid product ID."},
            status=400,
        )

    deleted, _ = WishlistItem.objects.filter(
        session_key=session_key,
        product_id=product_id,
    ).delete()

    if deleted == 0:
        return JsonResponse(
            {"success": False, "message": "Wishlist item not found."},
            status=404,
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Product removed from wishlist.",
        }
    )


@csrf_exempt
def wishlist_clear(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    data = json_body(request)

    if data is None:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400,
        )

    session_key = data.get("session_key")

    if not session_key:
        return JsonResponse(
            {"success": False, "message": "Session key is required."},
            status=400,
        )

    deleted, _ = WishlistItem.objects.filter(
        session_key=session_key,
    ).delete()

    return JsonResponse(
        {
            "success": True,
            "message": "Wishlist cleared successfully.",
            "deleted_count": deleted,
        }
    )


# =========================================================
# CUSTOMER REGISTER API
# =========================================================


@csrf_exempt
def customer_register(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    data = json_body(request)

    if data is None:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400,
        )

    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not username or not email or not password or not confirm_password:
        return JsonResponse(
            {"success": False, "message": "All fields are required."},
            status=400,
        )

    if len(username) > 150:
        return JsonResponse(
            {"success": False, "message": "Username is too long."},
            status=400,
        )

    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse(
            {"success": False, "message": "Username already exists."},
            status=400,
        )

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {"success": False, "message": "Email already registered."},
            status=400,
        )

    if password != confirm_password:
        return JsonResponse(
            {"success": False, "message": "Passwords do not match."},
            status=400,
        )

    try:
        validate_password(password)
    except ValidationError as errors:
        return JsonResponse(
            {
                "success": False,
                "message": "Password validation failed.",
                "errors": errors.messages,
            },
            status=400,
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Account created successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        },
        status=201,
    )


# =========================================================
# CUSTOMER LOGIN API
# =========================================================


@csrf_exempt
def customer_login(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    data = json_body(request)

    if data is None:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400,
        )

    username = str(data.get("username", "")).strip()
    password = data.get("password", "")

    if not username or not password:
        return JsonResponse(
            {"success": False, "message": "Username and password are required."},
            status=400,
        )

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse(
            {"success": False, "message": "Invalid username or password."},
            status=401,
        )

    if not user.is_active:
        return JsonResponse(
            {"success": False, "message": "Account is inactive."},
            status=403,
        )

    login(request, user)

    return JsonResponse(
        {
            "success": True,
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        },
        status=200,
    )


# =========================================================
# CUSTOMER LOGOUT API
# =========================================================


@csrf_exempt
def customer_logout(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "message": "You are not logged in."},
            status=401,
        )

    logout(request)

    return JsonResponse(
        {
            "success": True,
            "message": "Logout successful.",
        },
        status=200,
    )


# =========================================================
# CUSTOMER PROFILE API
# =========================================================


@csrf_exempt
def customer_profile(request):

    if request.method != "GET":
        return JsonResponse(
            {"success": False, "message": "GET method required."},
            status=405,
        )

    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "message": "Login required."},
            status=401,
        )

    user = request.user

    return JsonResponse(
        {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined.isoformat(),
            },
        },
        status=200,
    )


# =========================================================
# CUSTOMER PROFILE UPDATE API
# =========================================================


@csrf_exempt
def customer_profile_update(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "message": "Login required."},
            status=401,
        )

    data = json_body(request)

    if data is None:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400,
        )

    user = request.user

    first_name = str(data.get("first_name", user.first_name)).strip()
    last_name = str(data.get("last_name", user.last_name)).strip()
    email = str(data.get("email", user.email)).strip().lower()

    if not email:
        return JsonResponse(
            {"success": False, "message": "Email is required."},
            status=400,
        )

    if len(first_name) > 150 or len(last_name) > 150:
        return JsonResponse(
            {"success": False, "message": "Name fields cannot exceed 150 characters."},
            status=400,
        )

    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse(
            {"success": False, "message": "Invalid email address."},
            status=400,
        )

    if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
        return JsonResponse(
            {"success": False, "message": "Email already registered."},
            status=400,
        )

    user.first_name = first_name
    user.last_name = last_name
    user.email = email

    user.save(update_fields=["first_name", "last_name", "email"])

    return JsonResponse(
        {
            "success": True,
            "message": "Profile updated successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            },
        },
        status=200,
    )


# =========================================================
# CUSTOMER CHANGE PASSWORD API
# =========================================================


@csrf_exempt
def customer_change_password(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "POST method required."},
            status=405,
        )

    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "message": "Login required."},
            status=401,
        )

    data = json_body(request)

    if data is None:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400,
        )

    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if not old_password or not new_password or not confirm_password:
        return JsonResponse(
            {"success": False, "message": "All password fields are required."},
            status=400,
        )

    user = request.user

    if not user.check_password(old_password):
        return JsonResponse(
            {"success": False, "message": "Current password is incorrect."},
            status=400,
        )

    if new_password != confirm_password:
        return JsonResponse(
            {"success": False, "message": "New passwords do not match."},
            status=400,
        )

    if old_password == new_password:
        return JsonResponse(
            {
                "success": False,
                "message": "New password must be different from the current password.",
            },
            status=400,
        )

    try:
        validate_password(new_password, user=user)
    except ValidationError as errors:
        return JsonResponse(
            {
                "success": False,
                "message": "Password validation failed.",
                "errors": errors.messages,
            },
            status=400,
        )

    user.set_password(new_password)
    user.save(update_fields=["password"])

    update_session_auth_hash(request, user)

    return JsonResponse(
        {
            "success": True,
            "message": "Password changed successfully.",
        },
        status=200,
    )


# =========================================================
# CUSTOMER MY ORDERS
# =========================================================


@csrf_exempt
def customer_my_orders(request):

    if request.method != "GET":
        return JsonResponse(
            {"success": False, "message": "GET method required."}, status=405
        )

    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "message": "Login required."}, status=401
        )

    orders = Order.objects.filter(user=request.user).prefetch_related("items")

    order_list = []

    for order in orders:

        order_list.append(
            {
                "order_number": str(order.order_number),
                "status": order.status,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "subtotal": str(order.subtotal),
                "discount_amount": str(order.discount_amount),
                "shipping_cost": str(order.shipping_cost),
                "total_amount": str(order.total_amount),
                "created_at": order.created_at.isoformat(),
                "items": [
                    {
                        "product_name": item.product_name,
                        "product_image": item.product_image,
                        "quantity": item.quantity,
                        "unit_price": str(item.unit_price),
                        "total_price": str(item.total_price),
                    }
                    for item in order.items.all()
                ],
            }
        )

    return JsonResponse(
        {"success": True, "count": len(order_list), "orders": order_list}
    )
