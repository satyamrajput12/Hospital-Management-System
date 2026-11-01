from django.urls import path
from . import views

app_name = 'corepages'

urlpatterns = [
    # Core & Search
    path('', views.home, name='home'),
    path('search/', views.search_view, name='search'),

    # Pharmacy & Products
    path('pharmacy/', views.pharmacy_list, name='pharmacy_list'),
    path('pharmacy/<int:pk>/', views.product_detail, name='product_detail'),

    # Cart Operations
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/json/', views.cart_json, name='cart_json'),
    path('cart/add/', views.add_to_cart_api, name='add_to_cart_api'),
    path('cart/update/', views.update_cart_api, name='update_cart_api'),
    path('cart/remove/<int:pk>/', views.remove_cart_api, name='remove_cart_api'),

    # Checkout & Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),
    path('orders/my/', views.my_orders, name='my_orders'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/cancel/', views.cancel_order, name='cancel_order'),

    # Role Dashboards
    path('dashboard/', views.redirect_dashboard, name='redirect_dashboard'),
    path('dashboard/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    # Admin Commerce Management
    path('manage/products/', views.admin_product_list, name='admin_product_list'),
    path('manage/products/add/', views.admin_product_add, name='admin_product_add'),
    path('manage/products/add/', views.admin_product_add, name='admin_product_create'),
    path('manage/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('manage/products/<int:pk>/toggle/', views.admin_product_toggle, name='admin_product_toggle'),
    path('manage/orders/', views.admin_order_list, name='admin_order_list'),
    path('manage/orders/<int:pk>/update/', views.admin_order_update_status, name='admin_order_update_status'),
]
