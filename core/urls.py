# core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # ================= Branch Selection =================
    path('branch/select/', views.select_branch, name='select_branch'),
    path('branch/select/<int:branch_id>/', views.select_branch_by_id, name='select_branch_by_id'),
    path('branch/clear/', views.clear_branch, name='clear_branch'),
    path('set-branch/<int:branch_id>/', views.set_branch, name='set_branch'),  # ✅ only once

    # ================= Public Pages =================
    path('categories/', views.categories, name='categories'),
    path('products/', views.products, name='products'),  
    path('products/<int:category_id>/', views.products, name='products_by_category'),
    path('search/', views.search_products, name='search_products'),
    path('contact/', views.contact, name='contact'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('full-menu/', views.full_menu, name='full_menu'),

    # ================= Authentication =================
    path('register/', views.register_user, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='auth/user_login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('admin-login/', views.CustomAdminLoginView.as_view(), name='admin_login'),

    # ================= Cart =================
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),

    # ================= Checkout & Orders =================
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('track-order/<int:order_id>/', views.track_order, name='track_order'),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),

    # ================= Reviews =================
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),

    # ================= User Account =================
    path('my-account/', views.my_account, name='my_account'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),

    # ================= Admin Dashboard =================
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('admin-dashboard/orders/update/<int:order_id>/', views.update_order_status, name='update_order_status'),

    # ================= Category CRUD =================
    path('admin-dashboard/categories/', views.manage_categories, name='manage_categories'),
    path('admin-dashboard/categories/add/', views.add_category, name='add_category'),
    path('admin-dashboard/categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('admin-dashboard/categories/delete/<int:pk>/', views.delete_category, name='delete_category'),

    # ================= Product CRUD =================
    path('admin-dashboard/products/', views.manage_products, name='manage_products'),
    path('admin-dashboard/products/add/', views.add_product, name='add_product'),
    path('admin-dashboard/products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('admin-dashboard/products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path("loyalty/", views.loyalty_dashboard, name="loyalty_dashboard"),
    path("loyalty/apply/", views.apply_points, name="apply_points"),
    

]
