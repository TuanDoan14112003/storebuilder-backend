from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, ProductViewSet, create_order, get_store_orders, get_user_stores

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    path('store/<int:store_id>/order/', create_order, name='create_order'),
    path('store/<int:store_id>/orders/', get_store_orders, name='get_store_orders'),
    path('user/<int:user_id>/stores/', get_user_stores, name='get_user_stores'),
]