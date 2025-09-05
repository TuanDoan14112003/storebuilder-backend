from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from django.middleware.csrf import get_token
from django.http import JsonResponse
from .cart_service import CartService
from .serializers import (
    CartSerializer, AddToCartSerializer, UpdateCartItemSerializer, 
    CreateGuestOrderSerializer, OrderSerializer
)
from .models import Order, OrderItem


@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """Get CSRF token for frontend requests"""
    csrf_token = get_token(request)
    return JsonResponse({'csrf_token': csrf_token})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_cart(request):
    """Get current cart with all items"""
    cart_service = CartService(request)
    cart_summary = cart_service.get_cart_summary()
    
    serializer = CartSerializer(cart_service.get_or_create_cart(), context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_to_cart(request):
    """Add item to cart"""
    serializer = AddToCartSerializer(data=request.data)
    if serializer.is_valid():
        cart_service = CartService(request)
        try:
            cart_item = cart_service.add_item(
                product_id=serializer.validated_data['product_id'],
                quantity=serializer.validated_data['quantity']
            )
            
            # Return updated cart
            cart_serializer = CartSerializer(cart_service.get_or_create_cart(), context={'request': request})
            return Response({
                'message': 'Item added to cart successfully',
                'cart': cart_serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_cart_item(request, product_id):
    """Update cart item quantity"""
    serializer = UpdateCartItemSerializer(data=request.data)
    if serializer.is_valid():
        cart_service = CartService(request)
        try:
            cart_item = cart_service.update_item(
                product_id=product_id,
                quantity=serializer.validated_data['quantity']
            )
            
            # Return updated cart
            cart_serializer = CartSerializer(cart_service.get_or_create_cart(), context={'request': request})
            return Response({
                'message': 'Cart item updated successfully',
                'cart': cart_serializer.data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def remove_from_cart(request, product_id):
    """Remove item from cart"""
    cart_service = CartService(request)
    success = cart_service.remove_item(product_id)
    
    if success:
        # Return updated cart
        cart_serializer = CartSerializer(cart_service.get_or_create_cart(), context={'request': request})
        return Response({
            'message': 'Item removed from cart successfully',
            'cart': cart_serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({'error': 'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def clear_cart(request):
    """Clear all items from cart"""
    cart_service = CartService(request)
    cart_service.clear_cart()
    
    # Return empty cart
    cart_serializer = CartSerializer(cart_service.get_or_create_cart(), context={'request': request})
    return Response({
        'message': 'Cart cleared successfully',
        'cart': cart_serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def checkout(request):
    """Create order from cart items"""
    cart_service = CartService(request)
    cart_items = cart_service.get_cart_items()
    
    if not cart_items.exists():
        return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Group items by store
    stores_items = {}
    for item in cart_items:
        store_id = item.product.store.id
        if store_id not in stores_items:
            stores_items[store_id] = {
                'store': item.product.store,
                'items': [],
                'total': 0
            }
        stores_items[store_id]['items'].append(item)
        stores_items[store_id]['total'] += item.subtotal
    
    # Validate order data
    serializer = CreateGuestOrderSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    orders = []
    
    try:
        with transaction.atomic():
            # Create separate order for each store
            for store_data in stores_items.values():
                order = Order.objects.create(
                    customer=request.user if request.user.is_authenticated else None,
                    guest_email=serializer.validated_data.get('guest_email'),
                    guest_name=serializer.validated_data.get('guest_name'),
                    store=store_data['store'],
                    total_amount=store_data['total'],
                    shipping_address=serializer.validated_data['shipping_address'],
                    phone=serializer.validated_data['phone'],
                    notes=serializer.validated_data.get('notes', '')
                )
                
                # Create order items
                for cart_item in store_data['items']:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price
                    )
                
                orders.append(order)
            
            # Clear cart after successful order creation
            cart_service.clear_cart()
            
            # Merge guest cart if user just logged in
            if request.user.is_authenticated:
                cart_service.transfer_cart_on_login()
    
    except Exception as e:
        return Response({'error': 'Failed to create order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Return created orders
    order_serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response({
        'message': f'{len(orders)} order(s) created successfully',
        'orders': order_serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def merge_cart(request):
    """Merge guest cart to user cart on login"""
    if not request.user.is_authenticated:
        return Response({'error': 'User not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
    
    cart_service = CartService(request)
    success = cart_service.transfer_cart_on_login()
    
    if success:
        cart_serializer = CartSerializer(cart_service.get_or_create_cart(), context={'request': request})
        return Response({
            'message': 'Cart merged successfully',
            'cart': cart_serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({'message': 'No guest cart to merge'}, status=status.HTTP_200_OK)