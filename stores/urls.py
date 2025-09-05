from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, ProductViewSet, get_user_stores
from .cart_views import (
    get_csrf_token, get_cart, add_to_cart, update_cart_item, remove_from_cart, 
    clear_cart, checkout, merge_cart
)
from .order_views import (
    create_order, get_user_orders, get_store_orders, get_order_detail, update_order_status,
    approve_order, decline_order
)

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    path('user/<int:user_id>/stores/', get_user_stores, name='get_user_stores'),
    
    # CSRF endpoint
    path('csrf/', get_csrf_token, name='get_csrf_token'),
    
    # Cart endpoints
    path('cart/', get_cart, name='get_cart'),
    path('cart/add/', add_to_cart, name='add_to_cart'),
    path('cart/item/<int:product_id>/', update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', clear_cart, name='clear_cart'),
    path('cart/checkout/', checkout, name='checkout'),
    path('cart/merge/', merge_cart, name='merge_cart'),
    
    # Order endpoints
    path('orders/create/', create_order, name='create_order'),
    path('orders/user/', get_user_orders, name='get_user_orders'),
    path('orders/<int:order_id>/', get_order_detail, name='get_order_detail'),
    path('orders/<int:order_id>/status/', update_order_status, name='update_order_status'),
    path('orders/<int:order_id>/approve/', approve_order, name='approve_order'),
    path('orders/<int:order_id>/decline/', decline_order, name='decline_order'),
    path('store/<int:store_id>/orders/', get_store_orders, name='get_store_orders'),
]