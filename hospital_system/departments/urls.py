from django.urls import path
from . import views

app_name = 'departments'

urlpatterns = [
    # Public Department Views
    path('', views.department_list, name='list'),
    path('<int:pk>/', views.department_detail, name='detail'),

    # Public Diagnostic Lab Tests & Patient Bookings
    path('labs/', views.lab_test_list, name='lab_test_list'),
    path('labs/<int:pk>/', views.lab_test_detail, name='lab_test_detail'),
    path('labs/<int:pk>/book/', views.book_lab_test, name='book_lab_test'),
    path('labs/my/bookings/', views.my_lab_bookings, name='my_lab_bookings'),
    path('labs/<int:pk>/cancel/', views.cancel_lab_booking, name='cancel_lab_booking'),

    # Admin Department CRUD
    path('admin/manage/', views.admin_department_list, name='admin_list'),
    path('admin/manage/', views.admin_department_list, name='admin_dept_list'),
    path('admin/manage/add/', views.admin_department_add, name='admin_add'),
    path('admin/manage/add/', views.admin_department_add, name='admin_dept_create'),
    path('admin/manage/<int:pk>/edit/', views.admin_department_edit, name='admin_edit'),
    path('admin/manage/<int:pk>/edit/', views.admin_department_edit, name='admin_dept_edit'),
    path('admin/manage/<int:pk>/toggle/', views.admin_department_toggle, name='admin_toggle'),

    # Admin Lab Test CRUD & Bookings
    path('admin/labs/', views.admin_lab_test_list, name='admin_lab_test_list'),
    path('admin/labs/', views.admin_lab_test_list, name='admin_test_list'),
    path('admin/labs/add/', views.admin_lab_test_add, name='admin_lab_test_add'),
    path('admin/labs/add/', views.admin_lab_test_add, name='admin_test_create'),
    path('admin/labs/<int:pk>/edit/', views.admin_lab_test_edit, name='admin_lab_test_edit'),
    path('admin/labs/<int:pk>/edit/', views.admin_lab_test_edit, name='admin_test_edit'),
    path('admin/labs/<int:pk>/toggle/', views.admin_lab_test_toggle, name='admin_lab_test_toggle'),
    path('admin/lab-bookings/', views.admin_lab_booking_list, name='admin_lab_booking_list'),
    path('admin/lab-bookings/', views.admin_lab_booking_list, name='admin_booking_list'),
    path('admin/lab-bookings/<int:pk>/update/', views.admin_lab_booking_update, name='admin_lab_booking_update'),
    path('admin/lab-bookings/<int:pk>/update/', views.admin_lab_booking_update, name='admin_booking_update'),
]
