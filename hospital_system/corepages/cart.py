from django.db import transaction
from .models import Cart, CartItem, Product


def get_or_create_cart(request):
    """
    Retrieves or initializes a shopping cart.
    Automatically merges anonymous session cart items into authenticated user cart upon login.
    """
    if request.user.is_authenticated:
        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        # Check if an anonymous cart exists in session to merge
        session_cart_id = request.session.get('cart_id')
        if session_cart_id:
            try:
                anon_cart = Cart.objects.get(pk=session_cart_id, user__isnull=True)
                for item in anon_cart.items.all():
                    existing_item = user_cart.items.filter(product=item.product).first()
                    if existing_item:
                        existing_item.quantity += item.quantity
                        existing_item.save()
                    else:
                        item.cart = user_cart
                        item.save()
                anon_cart.delete()
                del request.session['cart_id']
            except Cart.DoesNotExist:
                pass
        return user_cart
    else:
        if not request.session.session_key:
            request.session.create()
        session_cart_id = request.session.get('cart_id')
        if session_cart_id:
            try:
                return Cart.objects.get(pk=session_cart_id, user__isnull=True)
            except Cart.DoesNotExist:
                pass
        cart = Cart.objects.create(session_key=request.session.session_key)
        request.session['cart_id'] = cart.pk
        return cart


def cart_to_dict(cart):
    """
    Serializes cart state for the off-canvas drawer and API responses.
    """
    items_data = []
    total = 0
    for item in cart.items.select_related('product').all():
        subtotal = float(item.subtotal())
        total += subtotal
        # Determine image URL
        img_url = ''
        if item.product.image:
            img_url = item.product.image.url
        elif item.product.image_url_fallback:
            img_url = item.product.image_url_fallback
        else:
            img_url = '/static/images/prod_1.jpg'

        items_data.append({
            'id': item.pk,
            'product_id': item.product.pk,
            'name': item.product.name,
            'price': float(item.product.effective_price),
            'quantity': item.quantity,
            'subtotal': subtotal,
            'image_url': img_url,
            'stock': item.product.stock,
        })

    return {
        'cart_id': cart.pk,
        'items': items_data,
        'total_items': sum(i['quantity'] for i in items_data),
        'subtotal': round(total, 2),
        'subtotal_formatted': f"₹{total:,.2f}",
    }
