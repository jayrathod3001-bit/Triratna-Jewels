"""
URL configuration for triratna project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from main.views import (
    home, about, privacy, terms, craftsmanship, promises, contact, logout_view, auth_view, 
    jewellery_detail, metal_price_api, subscribe_newsletter, catalog_view,
    cart_view, add_to_cart, remove_from_cart, update_cart_quantity,
    wishlist_view, add_to_wishlist, remove_from_wishlist, toggle_wishlist,
    process_checkout, order_success, profile_view, edit_profile, order_history, download_invoice,
    cancel_order_form, cancel_order_confirm, cancel_order_process, cancel_order_success, submit_review
)
from main.staff_views import (
    staff_logout, staff_dashboard,
    staff_jewellery_list, staff_jewellery_add, staff_jewellery_edit, staff_jewellery_delete,
    staff_order_list, staff_order_detail, staff_order_toggle_paid,
    staff_customer_list, staff_customer_detail,
    staff_banner_list, staff_banner_add, staff_banner_delete, staff_banner_toggle,
    staff_metal_price, staff_site_settings,
    staff_manage_list, staff_manage_add, staff_manage_toggle, staff_manage_delete,
    staff_newsletter_list, staff_newsletter_delete,
    staff_cancelled_orders,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('about/', about, name='about'),
    path('craftsmanship/', craftsmanship, name='craftsmanship'),
    path('promises/', promises, name='promises'),
    path('privacy/', privacy, name='privacy'),
    path('terms/', terms, name='terms'),
    path('contact/', contact, name='contact'),
    path('logout/', logout_view, name="logout"),
    path("login/", auth_view, name="login"),
    path("catalog/", catalog_view, name="catalog"),
    path("jewellery/<str:name>/", jewellery_detail, name="jewellery_detail"),
    path("jewellery/review/<int:jewellery_id>/", submit_review, name="submit_review"),
    path("api/metal-price/", metal_price_api, name="metal-price-api"),
    path("subscribe/", subscribe_newsletter, name="subscribe_newsletter"),
    
    # Profile
    path("profile/", profile_view, name="profile_view"),
    path("profile/edit/", edit_profile, name="edit_profile"),
    path("profile/orders/", order_history, name="order_history"),
    
    # Cart
    path('cart/', cart_view, name='cart_view'),
    path('cart/add/<int:jewellery_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/<str:action>/', update_cart_quantity, name='update_cart_quantity'),
    
    # Wishlist
    path('wishlist/', wishlist_view, name='wishlist_view'),
    path('wishlist/add/<int:jewellery_id>/', add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/toggle/<int:jewellery_id>/', toggle_wishlist, name='toggle_wishlist'),
    
    path('checkout/process/', process_checkout, name='process_checkout'),
    path('checkout/success/<int:order_id>/', order_success, name='order_success'),
    path('order/download/<int:order_id>/', download_invoice, name='download_invoice'),
    
    # Cancel Order
    path('cancel-order/', cancel_order_form, name='cancel_order_form'),
    path('cancel-order/<int:order_id>/<str:email>/', cancel_order_confirm, name='cancel_order_confirm'),
    path('cancel-order/process/<int:order_id>/', cancel_order_process, name='cancel_order_process'),
    path('cancel-order/success/', cancel_order_success, name='cancel_order_success'),
    
    # ============== STAFF ADMIN PANEL ==============
    path('staff-admin/', staff_dashboard, name='staff_dashboard'),
    path('staff-admin/logout/', staff_logout, name='staff_logout'),
    
    # Jewellery Management
    path('staff-admin/jewellery/', staff_jewellery_list, name='staff_jewellery_list'),
    path('staff-admin/jewellery/add/', staff_jewellery_add, name='staff_jewellery_add'),
    path('staff-admin/jewellery/edit/<int:pk>/', staff_jewellery_edit, name='staff_jewellery_edit'),
    path('staff-admin/jewellery/delete/<int:pk>/', staff_jewellery_delete, name='staff_jewellery_delete'),
    
    # Order Management
    path('staff-admin/orders/', staff_order_list, name='staff_order_list'),
    path('staff-admin/orders/<int:pk>/', staff_order_detail, name='staff_order_detail'),
    path('staff-admin/orders/<int:pk>/toggle-paid/', staff_order_toggle_paid, name='staff_order_toggle_paid'),
    
    # Customer Management
    path('staff-admin/customers/', staff_customer_list, name='staff_customer_list'),
    path('staff-admin/customers/<int:pk>/', staff_customer_detail, name='staff_customer_detail'),
    
    # Banner Management
    path('staff-admin/banners/', staff_banner_list, name='staff_banner_list'),
    path('staff-admin/banners/add/', staff_banner_add, name='staff_banner_add'),
    path('staff-admin/banners/delete/<int:pk>/', staff_banner_delete, name='staff_banner_delete'),
    path('staff-admin/banners/toggle/<int:pk>/', staff_banner_toggle, name='staff_banner_toggle'),
    
    # Metal Price
    path('staff-admin/metal-price/', staff_metal_price, name='staff_metal_price'),
    
    # Site Settings
    path('staff-admin/settings/', staff_site_settings, name='staff_site_settings'),
    
    # Staff Management
    path('staff-admin/staff/', staff_manage_list, name='staff_manage_list'),
    path('staff-admin/staff/add/', staff_manage_add, name='staff_manage_add'),
    path('staff-admin/staff/toggle/<int:pk>/', staff_manage_toggle, name='staff_manage_toggle'),
    path('staff-admin/staff/delete/<int:pk>/', staff_manage_delete, name='staff_manage_delete'),
    
    # Newsletter
    path('staff-admin/newsletter/', staff_newsletter_list, name='staff_newsletter_list'),
    path('staff-admin/newsletter/delete/<int:pk>/', staff_newsletter_delete, name='staff_newsletter_delete'),
    
    # Cancelled Orders
    path('staff-admin/cancelled-orders/', staff_cancelled_orders, name='staff_cancelled_orders'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)