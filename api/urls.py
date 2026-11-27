from django.urls import path
from . import views

urlpatterns = [
    path("", views.api_home, name="api_home"),
    # Products
    path("products/", views.products_list, name="products_list"),
    path("products/search/", views.product_search, name="product_search"),
    path("products/filter/", views.product_filter, name="product_filter"),
    path("products/sort/", views.product_sort, name="product_sort"),
    path("products/pagination/", views.product_pagination, name="product_pagination"),
    path(
        "products/stock-status/",
        views.product_stock_status,
        name="product_stock_status",
    ),
    path("products/featured/", views.featured_products, name="featured_products"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    # Reviews
    path(
        "products/<int:product_id>/reviews/",
        views.product_reviews,
        name="product_reviews",
    ),
    path(
        "products/<int:product_id>/reviews/submit/",
        views.submit_product_review,
        name="submit_product_review",
    ),
    # Categories
    path("categories/", views.categories_list, name="categories_list"),
    # Cart
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/update/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/", views.remove_cart_item, name="remove_cart_item"),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    # Checkout
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_history, name="order_history"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("coupons/validate/", views.validate_coupon, name="validate_coupon"),
    # Wishlist API
    path("wishlist/", views.wishlist_view, name="wishlist_view"),
    path("wishlist/add/", views.wishlist_add, name="wishlist_add"),
    path("wishlist/remove/", views.wishlist_remove, name="wishlist_remove"),
    path("wishlist/clear/", views.wishlist_clear, name="wishlist_clear"),
    path("auth/register/", views.customer_register, name="customer_register"),
    path("auth/login/", views.customer_login, name="customer_login"),
    path("auth/logout/", views.customer_logout, name="customer_logout"),
    path("auth/profile/", views.customer_profile, name="customer_profile"),
    path(
        "auth/profile/update/",
        views.customer_profile_update,
        name="customer_profile_update",
    ),
    path(
        "auth/change-password/",
        views.customer_change_password,
        name="customer_change_password",
    ),
    path(
        "auth/my-orders/",
        views.customer_my_orders,
        name="customer_my_orders",
    ),
]
