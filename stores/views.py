from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from django.shortcuts import get_object_or_404
from .models import Store, Product, Order, OrderItem
from .serializers import (StoreSerializer, StoreListSerializer, ProductSerializer, 
                         ProductCreateUpdateSerializer, OrderSerializer, OrderCreateSerializer)


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'products']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StoreListSerializer
        return StoreSerializer
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve', 'products']:
            return Store.objects.all()
        return Store.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        store = self.get_object()
        products = store.products.all()
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            return Product.objects.all()
        return Product.objects.filter(store__owner=self.request.user)
    
    def perform_create(self, serializer):
        store_id = self.request.data.get('store')
        store = get_object_or_404(Store, id=store_id, owner=self.request.user)
        serializer.save(store=store)
    
    def perform_update(self, serializer):
        store_id = self.request.data.get('store')
        if store_id:
            store = get_object_or_404(Store, id=store_id, owner=self.request.user)
            serializer.save(store=store)
        else:
            serializer.save()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_order(request, store_id):
    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = OrderCreateSerializer(data=request.data)
    if serializer.is_valid():
        order = serializer.save(customer=request.user, store=store)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_store_orders(request, store_id):
    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Only store owner can view orders
    if store.owner != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    orders = Order.objects.filter(store=store).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_user_stores(request, user_id):
    try:
        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    stores = Store.objects.filter(owner=user).order_by('name')
    serializer = StoreListSerializer(stores, many=True, context={'request': request})
    return Response(serializer.data)
