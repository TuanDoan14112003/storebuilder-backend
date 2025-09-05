from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, ProductViewSet, create_order, get_store_orders, get_user_stores
from .cart_views import (
    get_cart, add_to_cart, update_cart_item, remove_from_cart, 
    clear_cart, checkout, merge_cart
)

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    path('store/<int:store_id>/order/', create_order, name='create_order'),
    path('store/<int:store_id>/orders/', get_store_orders, name='get_store_orders'),
    path('user/<int:user_id>/stores/', get_user_stores, name='get_user_stores'),
    
    # Cart endpoints
    path('cart/', get_cart, name='get_cart'),
    path('cart/add/', add_to_cart, name='add_to_cart'),
    path('cart/item/<int:product_id>/', update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', clear_cart, name='clear_cart'),
    path('cart/checkout/', checkout, name='checkout'),
    path('cart/merge/', merge_cart, name='merge_cart'),
]