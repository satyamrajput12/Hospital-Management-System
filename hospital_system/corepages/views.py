import json
import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from accounts.decorators import patient_required, doctor_required, admin_required, verified_email_required
from accounts.models import User
from appointments.models import Appointment, MedicalRecord, Prescription
from departments.models import Department, LabTest, LabBooking
from doctors.models import Doctor
from .cart import get_or_create_cart, cart_to_dict
from .emails import send_order_confirmation_email
from .forms import CheckoutForm, ProductForm, ProductCategoryForm, OrderStatusUpdateForm
from .models import ProductCategory, Product, Cart, CartItem, Order, OrderItem, PaymentRecord


def home(request):
    """
    Homepage featuring live database records for departments, doctors, lab tests, and pharmacy products.
    """
    departments = Department.objects.filter(is_active=True)[:6]
    doctors = Doctor.objects.filter(is_active=True).select_related('user', 'department')[:6]
    lab_tests = LabTest.objects.filter(is_active=True).select_related('department')[:3]
    products = Product.objects.filter(is_active=True).select_related('category')[:4]

    return render(request, 'corepages/home.html', {
        'departments': departments,
        'doctors': doctors,
        'lab_tests': lab_tests,
        'products': products,
    })


def search_view(request):
    """
    Server-side search across doctors, departments, diagnostic tests, and pharmacy products.
    """
    query = request.GET.get('q', '').strip()
    active_tab = request.GET.get('tab', 'all')

    doctors = Doctor.objects.none()
    lab_tests = LabTest.objects.none()
    products = Product.objects.none()
    departments = Department.objects.none()

    if query:
        doctors = Doctor.objects.filter(is_active=True).filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(specialization__icontains=query) |
            Q(bio__icontains=query) |
            Q(department__name__icontains=query)
        ).select_related('user', 'department')

        lab_tests = LabTest.objects.filter(is_active=True).filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sample_type__icontains=query) |
            Q(department__name__icontains=query)
        ).select_related('department')

        products = Product.objects.filter(is_active=True).filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        ).select_related('category')

        departments = Department.objects.filter(is_active=True).filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    total_results = doctors.count() + lab_tests.count() + products.count() + departments.count()

    return render(request, 'corepages/search_results.html', {
        'query': query,
        'doctors': doctors,
        'lab_tests': lab_tests,
        'products': products,
        'departments': departments,
        'total_results': total_results,
        'active_tab': active_tab,
    })


def pharmacy_list(request):
    """
    Pharmacy catalog with category filtering, search, and server-side pagination.
    """
    products = Product.objects.filter(is_active=True).select_related('category')
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', '').strip()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'discount':
        products = products.order_by('-discount_percent')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = ProductCategory.objects.filter(is_active=True)

    return render(request, 'corepages/pharmacy_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_slug,
        'selected_sort': sort_by,
        'total_products': paginator.count,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(pk=product.pk)[:4]

    return render(request, 'corepages/product_detail.html', {
        'product': product,
        'related_products': related_products,
    })


# ==============================================================================
# SHOPPING CART VIEWS & APIS
# ==============================================================================

@require_GET
def cart_json(request):
    """
    Returns the current shopping cart state in JSON for the off-canvas drawer.
    """
    cart = get_or_create_cart(request)
    return JsonResponse(cart_to_dict(cart))


@require_POST
def add_to_cart_api(request):
    """
    Adds a product to the database-backed cart with server-side stock validation.
    Accepts both JSON and standard form POST requests.
    """
    # Extract product_id and quantity from JSON body or POST form data
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
        except (ValueError, KeyError):
            return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
    else:
        product_id = request.POST.get('product_id')
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1

    if not product_id or quantity <= 0:
        return JsonResponse({'success': False, 'error': 'Invalid product or quantity'}, status=400)

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = get_or_create_cart(request)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': 0})
    new_qty = item.quantity + quantity

    if new_qty > product.stock:
        error_msg = f"Only {product.stock} units of '{product.name}' are available in stock."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('core:cart_view')

    item.quantity = new_qty
    item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        cart_data = cart_to_dict(cart)
        return JsonResponse({'success': True, 'message': f"Added '{product.name}' to cart.", 'cart': cart_data})

    messages.success(request, f"Added '{product.name}' to your cart.")
    return redirect('core:cart_view')


@require_POST
def update_cart_api(request):
    """
    Updates the quantity of an existing item in the cart.
    """
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
            item_id = data.get('item_id')
            quantity = int(data.get('quantity', 1))
        except (ValueError, KeyError):
            return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
    else:
        item_id = request.POST.get('item_id')
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1

    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    if quantity <= 0:
        item.delete()
        msg = f"Removed '{item.product.name}' from your cart."
    elif quantity > item.product.stock:
        error_msg = f"Only {item.product.stock} units available in stock."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect('core:cart_view')
    else:
        item.quantity = quantity
        item.save()
        msg = "Cart updated."

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'success': True, 'message': msg, 'cart': cart_to_dict(cart)})

    messages.success(request, msg)
    return redirect('core:cart_view')


@require_POST
def remove_cart_api(request, pk):
    """
    Removes an item from the cart.
    """
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    product_name = item.product.name
    item.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'success': True,
            'message': f"Removed '{product_name}' from cart.",
            'cart': cart_to_dict(cart)
        })

    messages.success(request, f"Removed '{product_name}' from cart.")
    return redirect('core:cart_view')


def cart_view(request):
    """
    Full shopping cart page with item table, stock status, and subtotal calculation.
    """
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').all()
    subtotal = cart.total_amount()
    shipping = Decimal('0.00') if subtotal > 500 or subtotal == 0 else Decimal('40.00')
    total = subtotal + shipping

    return render(request, 'corepages/cart_view.html', {
        'cart': cart,
        'items': items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    })


# ==============================================================================
# CHECKOUT & ORDER MANAGEMENT
# ==============================================================================

@patient_required
@verified_email_required
def checkout_view(request):
    """
    Validates items, stock, calculates totals on backend,
    decrements inventory in a transaction, and places the order.
    """
    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').all()

    if not items.exists():
        messages.warning(request, "Your cart is currently empty. Add products before checking out.")
        return redirect('core:pharmacy_list')

    # Calculate backend total
    subtotal = Decimal('0.00')
    for item in items:
        # Check stock availability
        if item.quantity > item.product.stock:
            messages.error(
                request,
                f"Cannot proceed: '{item.product.name}' only has {item.product.stock} units in stock. "
                "Please update your cart quantity."
            )
            return redirect('core:cart_view')
        subtotal += item.subtotal()

    shipping = Decimal('0.00') if subtotal > 500 else Decimal('40.00')
    total = subtotal + shipping

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Generate unique order number
                    order_num = f"MED-{uuid.uuid4().hex[:8].upper()}"

                    order = Order.objects.create(
                        patient=request.user,
                        order_number=order_num,
                        full_name=form.cleaned_data['full_name'],
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        shipping_address=form.cleaned_data['shipping_address'],
                        city=form.cleaned_data['city'],
                        postal_code=form.cleaned_data['postal_code'],
                        total_amount=total,
                        payment_method=form.cleaned_data['payment_method'],
                        payment_status=Order.PaymentStatus.PAID if form.cleaned_data['payment_method'] == Order.PaymentMethod.DEV_SANDBOX else Order.PaymentStatus.COD,
                        notes=form.cleaned_data.get('notes', ''),
                        status=Order.Status.PROCESSING if form.cleaned_data['payment_method'] == Order.PaymentMethod.DEV_SANDBOX else Order.Status.PENDING,
                    )

                    # Create order items and safely decrement stock
                    for item in items:
                        product = Product.objects.select_for_update().get(pk=item.product.pk)
                        if item.quantity > product.stock:
                            raise ValueError(f"Insufficient stock for '{product.name}'. Available: {product.stock}")

                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            product_name=product.name,
                            unit_price=product.effective_price,
                            quantity=item.quantity,
                            subtotal=item.subtotal()
                        )

                        product.stock -= item.quantity
                        product.save()

                    # Record payment transaction
                    PaymentRecord.objects.create(
                        order=order,
                        transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                        payment_method=order.get_payment_method_display(),
                        amount=order.total_amount,
                        status="SUCCESSFUL" if order.payment_status == Order.PaymentStatus.PAID else "PENDING_COD",
                    )

                    # Clear user's cart
                    cart.items.all().delete()

                # Send confirmation email outside the atomic block
                send_order_confirmation_email(order)

                messages.success(request, f"Order #{order.order_number} successfully placed!")
                return redirect('core:order_confirmation', order_number=order.order_number)

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('core:cart_view')
    else:
        initial = {
            'full_name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'phone': request.user.phone,
            'shipping_address': request.user.address,
        }
        form = CheckoutForm(initial=initial)

    return render(request, 'corepages/checkout.html', {
        'form': form,
        'items': items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
    })


@patient_required
def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, patient=request.user)
    return render(request, 'corepages/order_confirmation.html', {'order': order})


@patient_required
def my_orders(request):
    orders = Order.objects.filter(patient=request.user).order_by('-created_at')
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'corepages/my_orders.html', {
        'page_obj': page_obj,
        'total_orders': paginator.count,
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)

    is_owner = (order.patient == request.user)
    is_adm = (request.user.is_superuser or request.user.is_admin_role())

    if not (is_owner or is_adm):
        raise PermissionDenied("Access Denied: You cannot view orders that do not belong to you.")

    return render(request, 'corepages/order_detail.html', {
        'order': order,
        'items': order.items.all(),
        'payments': order.payments.all(),
    })


@patient_required
@require_POST
def cancel_order(request, pk):
    """
    Patient cancels pending order; restores inventory safely via transaction.
    """
    order = get_object_or_404(Order, pk=pk)
    if order.patient != request.user and not (request.user.is_superuser or request.user.is_admin_role()):
        raise PermissionDenied("You are not authorized to cancel this order.")
    if not order.can_cancel():
        messages.error(request, "This order cannot be cancelled as it is already being shipped or completed.")
        return redirect('core:my_orders')

    with transaction.atomic():
        order.status = Order.Status.CANCELLED
        if order.payment_status == Order.PaymentStatus.PAID:
            order.payment_status = Order.PaymentStatus.REFUNDED
        order.save()

        # Restore product stock
        for item in order.items.all():
            if item.product:
                item.product.stock += item.quantity
                item.product.save()

    messages.success(request, f"Order #{order.order_number} has been cancelled and stock returned.")
    return redirect('core:my_orders')


# ==============================================================================
# DASHBOARDS
# ==============================================================================

@login_required
def redirect_dashboard(request):
    user = request.user
    if user.is_superuser or user.is_admin_role():
        return redirect('core:admin_dashboard')
    elif user.is_doctor_role():
        return redirect('core:doctor_dashboard')
    else:
        return redirect('core:patient_dashboard')


@patient_required
def patient_dashboard(request):
    user = request.user
    appointments = Appointment.objects.filter(patient=user).select_related('doctor__user', 'doctor__department')[:5]
    upcoming_count = Appointment.objects.filter(
        patient=user, status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
    ).count()

    recent_lab_bookings = LabBooking.objects.filter(patient=user).select_related('test')[:4]
    recent_orders = Order.objects.filter(patient=user).order_by('-created_at')[:4]
    recent_prescriptions = Prescription.objects.filter(patient=user).select_related('doctor__user')[:3]

    return render(request, 'corepages/patient_dashboard.html', {
        'appointments': appointments,
        'upcoming_count': upcoming_count,
        'recent_lab_bookings': recent_lab_bookings,
        'recent_orders': recent_orders,
        'recent_prescriptions': recent_prescriptions,
    })


@doctor_required
def doctor_dashboard(request):
    doctor = getattr(request.user, 'doctor_profile', None)
    appointments = []
    pending_count = confirmed_count = completed_count = 0
    today_appointments = []

    if doctor:
        appointments = Appointment.objects.filter(doctor=doctor).select_related('patient')[:6]
        pending_count = Appointment.objects.filter(doctor=doctor, status=Appointment.Status.PENDING).count()
        confirmed_count = Appointment.objects.filter(doctor=doctor, status=Appointment.Status.CONFIRMED).count()
        completed_count = Appointment.objects.filter(doctor=doctor, status=Appointment.Status.COMPLETED).count()

        today = timezone.localdate()
        today_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=today,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        ).select_related('patient')

    return render(request, 'corepages/doctor_dashboard.html', {
        'doctor': doctor,
        'appointments': appointments,
        'today_appointments': today_appointments,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
    })


@admin_required
def admin_dashboard(request):
    total_revenue = Order.objects.filter(
        payment_status__in=[Order.PaymentStatus.PAID, Order.PaymentStatus.COD]
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

    stats = {
        'total_doctors': Doctor.objects.count(),
        'total_patients': User.objects.filter(role=User.Role.PATIENT).count(),
        'total_departments': Department.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'pending_appointments': Appointment.objects.filter(status=Appointment.Status.PENDING).count(),
        'total_lab_bookings': LabBooking.objects.count(),
        'total_orders': Order.objects.count(),
        'total_revenue': total_revenue,
    }

    recent_appointments = Appointment.objects.select_related('doctor__user', 'patient').all()[:8]
    recent_orders = Order.objects.select_related('patient').all()[:6]

    return render(request, 'corepages/admin_dashboard.html', {
        'stats': stats,
        'recent_appointments': recent_appointments,
        'recent_orders': recent_orders,
    })


# ==============================================================================
# ADMIN COMMERCE MANAGEMENT VIEWS
# ==============================================================================

@admin_required
def admin_product_list(request):
    products = Product.objects.select_related('category').order_by('-created_at')
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query))

    paginator = Paginator(products, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'corepages/admin_product_list.html', {'page_obj': page_obj, 'query': query})


@admin_required
def admin_product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' added successfully.")
            return redirect('core:admin_product_list')
    else:
        form = ProductForm()
    return render(request, 'corepages/admin_product_form.html', {'form': form, 'title': 'Add Pharmacy Product'})


@admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('core:admin_product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'corepages/admin_product_form.html', {'form': form, 'title': f"Edit {product.name}", 'product': product})


@admin_required
@require_POST
def admin_product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save()
    status_str = "activated" if product.is_active else "deactivated"
    messages.success(request, f"Product '{product.name}' has been {status_str}.")
    return redirect('core:admin_product_list')


@admin_required
def admin_order_list(request):
    orders = Order.objects.select_related('patient').order_by('-created_at')
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()

    if status_filter:
        orders = orders.filter(status=status_filter)

    if query:
        orders = orders.filter(
            Q(order_number__icontains=query) |
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    paginator = Paginator(orders, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'corepages/admin_order_list.html', {
        'page_obj': page_obj,
        'status_choices': Order.Status.choices,
        'status_filter': status_filter,
        'query': query,
    })


@admin_required
def admin_order_update_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f"Order #{order.order_number} status updated to {order.get_status_display()}.")
            return redirect('core:admin_order_list')
    else:
        form = OrderStatusUpdateForm(instance=order)
    return render(request, 'corepages/admin_order_update.html', {'form': form, 'order': order})


# ==============================================================================
# PHASE 9: CUSTOM ERROR PAGES (400, 403, 404, 500)
# ==============================================================================

def custom_bad_request_view(request, exception=None):
    return render(request, 'errors/400.html', status=400)


def custom_permission_denied_view(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def custom_page_not_found_view(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def custom_server_error_view(request):
    return render(request, 'errors/500.html', status=500)
