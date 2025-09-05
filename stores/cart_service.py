from django.contrib.sessions.backends.base import SessionBase
from django.contrib.auth.models import User
from .models import Cart, CartItem, Product
from django.db import transaction


class CartService:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        self.user = request.user if request.user.is_authenticated else None
        
    def get_or_create_cart(self):
        """Get or create cart for authenticated user or guest session"""
        if self.user:
            cart, created = Cart.objects.get_or_create(user=self.user)
        else:
            # Ensure session exists
            if not self.session.session_key:
                self.session.create()
            cart, created = Cart.objects.get_or_create(session_key=self.session.session_key)
        return cart
    
    def add_item(self, product_id, quantity=1):
        """Add item to cart"""
        try:
            product = Product.objects.get(id=product_id)
            cart = self.get_or_create_cart()
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
                
            return cart_item
        except Product.DoesNotExist:
            raise ValueError("Product not found")
    
    def update_item(self, product_id, quantity):
        """Update item quantity in cart"""
        cart = self.get_or_create_cart()
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            if quantity <= 0:
                cart_item.delete()
                return None
            else:
                cart_item.quantity = quantity
                cart_item.save()
                return cart_item
        except CartItem.DoesNotExist:
            raise ValueError("Item not found in cart")
    
    def remove_item(self, product_id):
        """Remove item from cart"""
        cart = self.get_or_create_cart()
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            cart_item.delete()
            return True
        except CartItem.DoesNotExist:
            return False
    
    def get_cart_items(self):
        """Get all items in cart"""
        cart = self.get_or_create_cart()
        return cart.items.select_related('product').all()
    
    def get_cart_summary(self):
        """Get cart summary with totals"""
        cart = self.get_or_create_cart()
        items = self.get_cart_items()
        return {
            'items': items,
            'total_items': cart.total_items,
            'total_amount': cart.total_amount,
            'cart_id': cart.id
        }
    
    def clear_cart(self):
        """Clear all items from cart"""
        cart = self.get_or_create_cart()
        cart.items.all().delete()
    
    @transaction.atomic
    def merge_guest_cart_to_user(self, session_key):
        """Merge guest cart to authenticated user cart"""
        if not self.user:
            return False
            
        try:
            # Get guest cart
            guest_cart = Cart.objects.get(session_key=session_key)
            user_cart = self.get_or_create_cart()
            
            # Merge items
            for guest_item in guest_cart.items.all():
                user_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=guest_item.product,
                    defaults={'quantity': guest_item.quantity}
                )
                
                if not created:
                    user_item.quantity += guest_item.quantity
                    user_item.save()
            
            # Delete guest cart
            guest_cart.delete()
            return True
            
        except Cart.DoesNotExist:
            return False
    
    def transfer_cart_on_login(self):
        """Transfer guest cart to user cart on login"""
        if self.session.session_key:
            return self.merge_guest_cart_to_user(self.session.session_key)
        return False