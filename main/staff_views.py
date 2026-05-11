from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .models import (
    Banner, Jewellery, RegisterUser, MetalPrice,
    CartItem, WishlistItem, SiteSetting, NewsletterSubscriber,
    Order, OrderItem, StaffUser, CancelledOrder
)
from .views import auto_cancel_invalid_pay_at_shop_orders


# ============== HELPER ==============
def get_staff_user(request):
    """Get the currently logged-in staff user from session."""
    staff_id = request.session.get('staff_id')
    if staff_id:
        try:
            return StaffUser.objects.get(id=staff_id, is_active=True)
        except StaffUser.DoesNotExist:
            return None
    return None


def staff_required(view_func):
    """Decorator to require staff login."""
    def wrapper(request, *args, **kwargs):
        staff = get_staff_user(request)
        if not staff:
            messages.error(request, "Please login to access the admin panel.")
            return redirect('login')
        request.staff_user = staff
        return view_func(request, *args, **kwargs)
    return wrapper


# ============== AUTH ==============
def staff_logout(request):
    keys_to_remove = ['staff_id', 'staff_name', 'staff_role']
    for key in keys_to_remove:
        request.session.pop(key, None)
    messages.success(request, "Logged out successfully.")
    return redirect('login')


# ============== DASHBOARD ==============
@staff_required
def staff_dashboard(request):
    auto_cancel_invalid_pay_at_shop_orders()
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    
    total_products = Jewellery.objects.count()
    total_customers = RegisterUser.objects.count()
    total_orders = Order.objects.filter(payment_method='online').count()
    total_revenue = Order.objects.filter(payment_method='online').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    recent_orders = Order.objects.order_by('-order_date')[:5]
    # Daily stats for chart (last 7 days)
    chart_labels = []
    chart_orders = []
    chart_cancels = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        chart_labels.append(day.strftime('%d %b'))
        chart_orders.append(Order.objects.filter(order_date__date=day).count())
        chart_cancels.append(CancelledOrder.objects.filter(cancelled_at__date=day).count())

    # Metal Price history for chart
    gold_prices = []
    silver_prices = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        price = MetalPrice.objects.filter(updated_at__date=day).order_by('-updated_at').first()
        if not price:
            price = MetalPrice.objects.filter(updated_at__date__lt=day).order_by('-updated_at').first()
        gold_prices.append(float(price.gold_price) if price else 0)
        silver_prices.append(float(price.silver_price) if price else 0)

    top_selling = OrderItem.objects.values('jewellery__name').annotate(sales_count=Sum('quantity')).order_by('-sales_count')[:5]
    
    orders_today = Order.objects.filter(order_date__date=today, payment_method='online').count()
    revenue_today = Order.objects.filter(order_date__date=today, payment_method='online').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    pending_pickups = Order.objects.filter(payment_method='pay_at_shop', is_paid=False).count()
    pending_pickup_value = Order.objects.filter(payment_method='pay_at_shop', is_paid=False).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    shop_orders_count = Order.objects.filter(payment_method='pay_at_shop').count()
    shop_orders_value = Order.objects.filter(payment_method='pay_at_shop').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    out_of_stock = Jewellery.objects.filter(is_in_stock=False).count()
    subscribers = NewsletterSubscriber.objects.count()
    
    cancelled_count = CancelledOrder.objects.count()
    total_refunded = CancelledOrder.objects.aggregate(Sum('refund_amount'))['refund_amount__sum'] or 0
    
    context = {
        'active_page': 'dashboard',
        'staff': request.staff_user,
        'total_products': total_products,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'top_selling': top_selling,
        'orders_today': orders_today,
        'revenue_today': revenue_today,
        'pending_pickups': pending_pickups,
        'pending_pickup_value': pending_pickup_value,
        'shop_orders_count': shop_orders_count,
        'shop_orders_value': shop_orders_value,
        'out_of_stock': out_of_stock,
        'subscribers': subscribers,
        'chart_labels': json.dumps(chart_labels),
        'chart_orders': json.dumps(chart_orders),
        'chart_cancels': json.dumps(chart_cancels),
        'gold_prices': json.dumps(gold_prices),
        'silver_prices': json.dumps(silver_prices),
        'cancelled_count': cancelled_count,
        'total_refunded': total_refunded,
    }
    return render(request, 'staff_admin/dashboard.html', context)


# ============== JEWELLERY CRUD ==============
@staff_required
def staff_jewellery_list(request):
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    material_filter = request.GET.get('material', '')
    stock_filter = request.GET.get('stock', '')
    
    items = Jewellery.objects.all().order_by('-id')
    
    if search:
        items = items.filter(Q(name__icontains=search))
    if category_filter:
        items = items.filter(category__id=category_filter)
    if material_filter:
        items = items.filter(material_type=material_filter)
    if stock_filter == 'in_stock':
        items = items.filter(is_in_stock=True)
    elif stock_filter == 'out_of_stock':
        items = items.filter(is_in_stock=False)
    
    # Convert to int for template comparison
    selected_cat_id = None
    if category_filter:
        try:
            selected_cat_id = int(category_filter)
        except ValueError:
            selected_cat_id = None
    
    context = {
        'active_page': 'jewellery',
        'staff': request.staff_user,
        'items': items,
        'material_choices': Jewellery.MATERIAL_CHOICES,
        'search': search,
        'material_filter': material_filter,
        'stock_filter': stock_filter,
    }
    return render(request, 'staff_admin/jewellery_list.html', context)


@staff_required
def staff_jewellery_add(request):
    if request.method == 'POST':
        try:
            jewellery = Jewellery(
                name=request.POST.get('name'),
                type=request.POST.get('type'),
                material_type=request.POST.get('material_type'),
                weight=Decimal(request.POST.get('weight', '0')),
                karat=request.POST.get('karat', 'NA'),
                manual_rate=Decimal(request.POST.get('manual_rate', '0')),
                stock_quantity=int(request.POST.get('stock_quantity', '1')),
                is_featured=request.POST.get('is_featured') == 'on',
                description=request.POST.get('description', ''),
            )
            if request.FILES.get('image'):
                jewellery.image = request.FILES['image']
            jewellery.save()
            messages.success(request, f"'{jewellery.name}' added successfully!")
            return redirect('staff_jewellery_list')
        except Exception as e:
            messages.error(request, f"Error: {e}")
    
    context = {
        'active_page': 'jewellery',
        'staff': request.staff_user,
        'type_choices': Jewellery.TYPE_CHOICES,
        'material_choices': Jewellery.MATERIAL_CHOICES,
    }
    return render(request, 'staff_admin/jewellery_form.html', context)


@staff_required
def staff_jewellery_edit(request, pk):
    jewellery = get_object_or_404(Jewellery, pk=pk)
    
    if request.method == 'POST':
        try:
            jewellery.name = request.POST.get('name')
            jewellery.type = request.POST.get('type')
            jewellery.material_type = request.POST.get('material_type')
            jewellery.weight = Decimal(request.POST.get('weight', '0'))
            jewellery.karat = request.POST.get('karat', 'NA')
            jewellery.manual_rate = Decimal(request.POST.get('manual_rate', '0'))
            jewellery.stock_quantity = int(request.POST.get('stock_quantity', '1'))
            jewellery.is_featured = request.POST.get('is_featured') == 'on'
            jewellery.description = request.POST.get('description', '')
            if request.FILES.get('image'):
                jewellery.image = request.FILES['image']
            jewellery.save()
            messages.success(request, f"'{jewellery.name}' updated successfully!")
            return redirect('staff_jewellery_list')
        except Exception as e:
            messages.error(request, f"Error: {e}")
    
    context = {
        'active_page': 'jewellery',
        'staff': request.staff_user,
        'jewellery': jewellery,
        'type_choices': Jewellery.TYPE_CHOICES,
        'material_choices': Jewellery.MATERIAL_CHOICES,
    }
    return render(request, 'staff_admin/jewellery_form.html', context)


@staff_required
def staff_jewellery_delete(request, pk):
    jewellery = get_object_or_404(Jewellery, pk=pk)
    name = jewellery.name
    jewellery.delete()
    messages.success(request, f"'{name}' deleted successfully!")
    return redirect('staff_jewellery_list')

# ============== ORDER MANAGEMENT ==============
@staff_required
def staff_order_list(request):
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    method_filter = request.GET.get('method', '')
    
    orders = Order.objects.all().order_by('-order_date').prefetch_related('items__jewellery')
    
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    if status_filter == 'paid':
        orders = orders.filter(is_paid=True)
    elif status_filter == 'pending':
        orders = orders.filter(is_paid=False)
    if method_filter:
        orders = orders.filter(payment_method=method_filter)
    
    context = {
        'active_page': 'orders',
        'staff': request.staff_user,
        'orders': orders,
        'search': search,
        'status_filter': status_filter,
        'method_filter': method_filter,
    }
    return render(request, 'staff_admin/order_list.html', context)


@staff_required
def staff_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    context = {
        'active_page': 'orders',
        'staff': request.staff_user,
        'order': order,
        'items': order.items.all(),
    }
    return render(request, 'staff_admin/order_detail.html', context)


@staff_required
def staff_order_toggle_paid(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order.is_paid = not order.is_paid
    order.save()
    status = "Paid" if order.is_paid else "Pending"
    messages.success(request, f"Order #{order.id} marked as {status}.")
    return redirect('staff_order_detail', pk=pk)


# ============== CUSTOMER MANAGEMENT ==============
@staff_required
def staff_customer_list(request):
    search = request.GET.get('search', '')
    customers = RegisterUser.objects.all().order_by('-id')
    
    if search:
        customers = customers.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    context = {
        'active_page': 'customers',
        'staff': request.staff_user,
        'customers': customers,
        'search': search,
    }
    return render(request, 'staff_admin/customer_list.html', context)


@staff_required
def staff_customer_detail(request, pk):
    customer = get_object_or_404(RegisterUser, pk=pk)
    orders = Order.objects.filter(user=customer).order_by('-order_date')
    total_spent = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    context = {
        'active_page': 'customers',
        'staff': request.staff_user,
        'customer': customer,
        'orders': orders,
        'total_spent': total_spent,
    }
    return render(request, 'staff_admin/customer_detail.html', context)


# ============== BANNER MANAGEMENT ==============
@staff_required
def staff_banner_list(request):
    banners = Banner.objects.all().order_by('-id')
    context = {
        'active_page': 'banners',
        'staff': request.staff_user,
        'banners': banners,
    }
    return render(request, 'staff_admin/banner_list.html', context)


@staff_required
def staff_banner_add(request):
    if request.method == 'POST':
        try:
            banner = Banner(
                page=request.POST.get('page', 'home'),
                heading=request.POST.get('heading', ''),
                subheading=request.POST.get('subheading', ''),
                button_text=request.POST.get('button_text', ''),
                button_link=request.POST.get('button_link', ''),
                is_active=request.POST.get('is_active') == 'on',
            )
            if request.FILES.get('image'):
                banner.image = request.FILES['image']
            banner.save()
            messages.success(request, "Banner added successfully!")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('staff_banner_list')


@staff_required
def staff_banner_delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.delete()
    messages.success(request, "Banner deleted!")
    return redirect('staff_banner_list')


@staff_required
def staff_banner_toggle(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.is_active = not banner.is_active
    banner.save()
    status = "activated" if banner.is_active else "deactivated"
    messages.success(request, f"Banner {status}!")
    return redirect('staff_banner_list')


# ============== METAL PRICE MANAGEMENT ==============
@staff_required
def staff_metal_price(request):
    if request.method == 'POST':
        try:
            gold = Decimal(request.POST.get('gold_price', '0'))
            silver = Decimal(request.POST.get('silver_price', '0'))
            MetalPrice.objects.create(gold_price=gold, silver_price=silver)
            messages.success(request, "Metal prices updated successfully!")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('staff_metal_price')
    
    prices = MetalPrice.objects.order_by('-updated_at')[:20]
    latest = MetalPrice.objects.last()
    
    context = {
        'active_page': 'metal_price',
        'staff': request.staff_user,
        'prices': prices,
        'latest': latest,
    }
    return render(request, 'staff_admin/metal_price.html', context)


# ============== SITE SETTINGS ==============
@staff_required
def staff_site_settings(request):
    setting = SiteSetting.objects.first()
    
    if request.method == 'POST':
        if not setting:
            setting = SiteSetting()
        setting.whatsapp_number = request.POST.get('whatsapp_number', '')
        setting.goldapi_key = request.POST.get('goldapi_key', '')
        setting.active_making_charge_percent = Decimal(request.POST.get('active_making_charge_percent', '3.00') or '3.00')
        setting.save()
        messages.success(request, "Settings updated successfully!")
        return redirect('staff_site_settings')
    
    context = {
        'active_page': 'settings',
        'staff': request.staff_user,
        'setting': setting,
    }
    return render(request, 'staff_admin/site_settings.html', context)


# ============== STAFF MANAGEMENT ==============
@staff_required
def staff_manage_list(request):
    staff_members = StaffUser.objects.all().order_by('-created_at')
    context = {
        'active_page': 'staff',
        'staff': request.staff_user,
        'staff_members': staff_members,
    }
    return render(request, 'staff_admin/staff_list.html', context)


@staff_required
def staff_manage_add(request):
    if request.method == 'POST':
        try:
            if request.staff_user.role != 'manager':
                messages.error(request, "Only managers can add staff members.")
                return redirect('staff_manage_list')

            role = request.POST.get('role', 'sales')
            if role == 'manager':
                messages.error(request, "Only the Owner can add a Manager. Please use Django Admin.")
                return redirect('staff_manage_list')
                
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            
            if StaffUser.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
            elif name and email and password:
                StaffUser.objects.create(name=name, email=email, password=password, role=role)
                messages.success(request, f"Staff '{name}' added successfully!")
            else:
                messages.error(request, "All fields are required.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('staff_manage_list')


@staff_required
def staff_manage_toggle(request, pk):
    member = get_object_or_404(StaffUser, pk=pk)
    
    if member.role == 'manager':
        messages.error(request, "Only the Owner can update a Manager.")
        return redirect('staff_manage_list')
        
    if request.staff_user.role != 'manager':
        messages.error(request, "Only managers can update staff members.")
        return redirect('staff_manage_list')
        
    member.is_active = not member.is_active
    member.save()
    status = "activated" if member.is_active else "deactivated"
    messages.success(request, f"Staff '{member.name}' {status}!")
    return redirect('staff_manage_list')


@staff_required
def staff_manage_delete(request, pk):
    member = get_object_or_404(StaffUser, pk=pk)
    
    if member.role == 'manager':
        messages.error(request, "Only the Owner can delete a Manager.")
        return redirect('staff_manage_list')
        
    if request.staff_user.role != 'manager':
        messages.error(request, "Only managers can delete staff members.")
        return redirect('staff_manage_list')
        
    if member.id == request.staff_user.id:
        messages.error(request, "You cannot delete yourself!")
    else:
        name = member.name
        member.delete()
        messages.success(request, f"Staff '{name}' deleted!")
    return redirect('staff_manage_list')


# ============== NEWSLETTER ==============
@staff_required
def staff_newsletter_list(request):
    subscribers = NewsletterSubscriber.objects.all().order_by('-subscribed_at')
    context = {
        'active_page': 'newsletter',
        'staff': request.staff_user,
        'subscribers': subscribers,
    }
    return render(request, 'staff_admin/newsletter_list.html', context)


@staff_required
def staff_newsletter_delete(request, pk):
    sub = get_object_or_404(NewsletterSubscriber, pk=pk)
    sub.delete()
    messages.success(request, "Subscriber removed!")
    return redirect('staff_newsletter_list')


# ============== CANCELLED ORDERS ==============
@staff_required
def staff_cancelled_orders(request):
    cancelled = CancelledOrder.objects.all().order_by('-cancelled_at')
    total_refunded = cancelled.aggregate(Sum('refund_amount'))['refund_amount__sum'] or 0
    total_charges = cancelled.aggregate(Sum('cancellation_charge'))['cancellation_charge__sum'] or 0
    context = {
        'active_page': 'cancelled',
        'staff': request.staff_user,
        'cancelled_orders': cancelled,
        'total_refunded': total_refunded,
        'total_charges': total_charges,
    }
    return render(request, 'staff_admin/cancelled_orders.html', context)


