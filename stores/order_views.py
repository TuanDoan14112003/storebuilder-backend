from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth.models import User
from .models import Order, OrderItem, Product, Store
from .serializers import OrderSerializer, CreateGuestOrderSerializer, OrderItemSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    """Create a new order (for authenticated users or guests)"""
    # Validate order data
    serializer = CreateGuestOrderSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get items from request
    items_data = request.data.get('items', [])
    if not items_data:
        return Response({'error': 'Order must contain at least one item'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Group items by store
    stores_items = {}
    total_order_amount = 0
    
    for item_data in items_data:
        try:
            product = Product.objects.get(id=item_data['product_id'])
            quantity = item_data['quantity']
            
            if quantity <= 0:
                return Response({'error': f'Invalid quantity for product {product.name}'}, status=status.HTTP_400_BAD_REQUEST)
            
            store_id = product.store.id
            if store_id not in stores_items:
                stores_items[store_id] = {
                    'store': product.store,
                    'items': [],
                    'total': 0
                }
            
            item_total = product.price * quantity
            stores_items[store_id]['items'].append({
                'product': product,
                'quantity': quantity,
                'price': product.price
            })
            stores_items[store_id]['total'] += item_total
            total_order_amount += item_total
            
        except Product.DoesNotExist:
            return Response({'error': f'Product with ID {item_data["product_id"]} not found'}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return Response({'error': 'Each item must have product_id and quantity'}, status=status.HTTP_400_BAD_REQUEST)
    
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
                for item_data in store_data['items']:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data['product'],
                        quantity=item_data['quantity'],
                        price=item_data['price']
                    )
                
                orders.append(order)
    
    except Exception as e:
        return Response({'error': 'Failed to create order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Return created orders
    order_serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response({
        'message': f'{len(orders)} order(s) created successfully',
        'orders': order_serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_orders(request):
    """Get all orders for authenticated user"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    
    # Optional filtering by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response({
        'count': orders.count(),
        'orders': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_store_orders(request, store_id):
    """Get all orders for a specific store (store owner only)"""
    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return Response({'error': 'Store not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user owns the store
    if store.owner != request.user:
        return Response({'error': 'You do not have permission to view this store\'s orders'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    orders = Order.objects.filter(store=store).order_by('-created_at')
    
    # Optional filtering by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response({
        'store_name': store.name,
        'count': orders.count(),
        'orders': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_order_detail(request, order_id):
    """Get details of a specific order"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if request.user.is_authenticated:
        # User can see their own orders or orders from their stores
        if order.customer != request.user and order.store.owner != request.user:
            return Response({'error': 'You do not have permission to view this order'}, 
                           status=status.HTTP_403_FORBIDDEN)
    else:
        # For unauthenticated users, they need to be the guest who placed the order
        # This could be implemented with a token/email verification system
        return Response({'error': 'Authentication required to view order details'}, 
                       status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = OrderSerializer(order, context={'request': request})
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status (store owner only)"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user owns the store
    if order.store.owner != request.user:
        return Response({'error': 'You do not have permission to update this order'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    new_status = request.data.get('status')
    if not new_status:
        return Response({'error': 'Status field is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate status
    valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response({'error': f'Invalid status. Valid choices: {valid_statuses}'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    order.status = new_status
    order.save()
    
    serializer = OrderSerializer(order, context={'request': request})
    return Response({
        'message': 'Order status updated successfully',
        'order': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_order(request, order_id):
    """Approve/confirm an order (store owner only)"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user owns the store
    if order.store.owner != request.user:
        return Response({'error': 'You do not have permission to approve this order'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    # Check if order can be approved
    if order.status != 'pending':
        return Response({'error': f'Cannot approve order with status: {order.status}. Only pending orders can be approved.'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Approve the order
    order.status = 'confirmed'
    order.save()
    
    serializer = OrderSerializer(order, context={'request': request})
    return Response({
        'message': 'Order approved successfully',
        'order': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_order(request, order_id):
    """Decline/cancel an order (store owner only)"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user owns the store
    if order.store.owner != request.user:
        return Response({'error': 'You do not have permission to decline this order'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    # Check if order can be declined
    if order.status in ['delivered', 'cancelled']:
        return Response({'error': f'Cannot decline order with status: {order.status}'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    # Get decline reason from request (optional)
    decline_reason = request.data.get('reason', '')
    
    # Decline the order
    order.status = 'cancelled'
    if decline_reason:
        # Add reason to notes
        current_notes = order.notes or ''
        order.notes = f"{current_notes}\n\nDeclined: {decline_reason}".strip()
    order.save()
    
    serializer = OrderSerializer(order, context={'request': request})
    return Response({
        'message': 'Order declined successfully',
        'order': serializer.data
    })