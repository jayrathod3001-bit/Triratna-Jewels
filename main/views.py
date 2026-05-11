from django.shortcuts import render,redirect,get_object_or_404
from .models import Banner, Jewellery, RegisterUser, MetalPrice, CartItem, WishlistItem, SiteSetting, NewsletterSubscriber, Order, OrderItem, StaffUser, CancelledOrder, ProductReview
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q
import json
import requests
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .email_utils import send_welcome_email, send_order_email, send_cancel_email, generate_order_pdf

def get_current_user(request):
    user_id = request.session.get("user_id")
    if user_id:
        try:
            return RegisterUser.objects.get(id=user_id)
        except RegisterUser.DoesNotExist:
            return None
    return None

def get_session_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

def get_common_context(request):
    user = get_current_user(request)
    session_id = get_session_id(request)
    
    cart_count = 0
    wishlist_count = 0
    wishlist_ids = []
    
    if user:
        cart_count = CartItem.objects.filter(user=user).aggregate(Sum('quantity'))['quantity__sum'] or 0
        wishlist_count = WishlistItem.objects.filter(user=user, moved_to_cart=False).count()
        wishlist_ids = list(WishlistItem.objects.filter(user=user).values_list('jewellery_id', flat=True))
    else:
        # For guests, check by session_id
        cart_count = CartItem.objects.filter(session_id=session_id).aggregate(Sum('quantity'))['quantity__sum'] or 0
        wishlist_count = WishlistItem.objects.filter(session_id=session_id, moved_to_cart=False).count()
        wishlist_ids = list(WishlistItem.objects.filter(session_id=session_id).values_list('jewellery_id', flat=True))
        
    site_setting = SiteSetting.objects.first()
    whatsapp_number = site_setting.whatsapp_number if (site_setting and site_setting.whatsapp_number) else "919876543210"

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'wishlist_ids': wishlist_ids,
        'MEDIA_URL': settings.MEDIA_URL,
        'whatsapp_number': whatsapp_number,
    }

def auto_cancel_invalid_pay_at_shop_orders():
    today = timezone.now().date()
    
    # Combine using Q objects to avoid the "Cannot combine unique with non-unique" error
    orders_to_cancel = Order.objects.filter(
        Q(pickup_date__lt=today) | Q(items__jewellery__stock_quantity=0),
        payment_method='pay_at_shop',
        is_paid=False
    ).distinct()
    
    for order in orders_to_cancel:
        is_expired = order.pickup_date and order.pickup_date < today
        reason = "Expired: Not picked up by date" if is_expired else "Item sold out / Out of Stock"
        
        items_data = []
        for item in order.items.all():
            items_data.append({
                'jewellery_name': item.jewellery.name,
                'jewellery_id': item.jewellery.id,
                'quantity': item.quantity,
                'price': str(item.price),
                'line_total': str(item.line_total),
            })
            
            # Restore stock ONLY if cancelled due to expiration. 
            # If cancelled because stock became 0, the physical item is actually gone.
            if is_expired:
                item.jewellery.stock_quantity += item.quantity
                item.jewellery.sales_count = max(0, item.jewellery.sales_count - item.quantity)
                item.jewellery.save()
                
        CancelledOrder.objects.create(
            original_order_id=order.id,
            user=order.user,
            base_amount=order.base_amount,
            making_charges=order.making_charges,
            gst_amount=order.gst_amount,
            total_amount=order.total_amount,
            refund_amount=Decimal('0.00'),
            cancellation_charge=Decimal('0.00'),
            charge_percentage=Decimal('0.00'),
            payment_method=order.payment_method,
            order_date=order.order_date,
            items_data=items_data,
            reason=reason
        )
        
        # Optionally send email about auto-cancellation
        try:
            cancelled_obj = CancelledOrder.objects.get(original_order_id=order.id)
            send_cancel_email(cancelled_obj, order.user)
        except Exception:
            pass
            
        order.delete()

def home(request):
    auto_cancel_invalid_pay_at_shop_orders()
    banners = Banner.objects.filter(page='home', is_active=True)
    search_query = request.GET.get('search', '').strip()
    selected_types = request.GET.getlist('type')
    selected_categories = request.GET.getlist('category')
    selected_karats = request.GET.getlist('karat')
    selected_materials = request.GET.getlist('material')
    in_stock_only = request.GET.get('in_stock') == 'true'

    # If any filtering or searching is active, look through all jewellery
    if search_query or selected_types or selected_categories or selected_karats or selected_materials or in_stock_only:
        jewellery = Jewellery.objects.all()
    else:
        jewellery = Jewellery.objects.filter(is_featured=True)

    if selected_types:
        jewellery = jewellery.filter(type__in=selected_types)
    if selected_categories:
        jewellery = jewellery.filter(category__name__in=selected_categories)
    if selected_karats:
        jewellery = jewellery.filter(karat__in=selected_karats)
    if selected_materials:
        jewellery = jewellery.filter(material_type__in=selected_materials)
    
    if in_stock_only:
        jewellery = jewellery.filter(is_in_stock=True)
    
    if search_query:
        query = search_query.lower().strip()
        if query.endswith('s') and not query.endswith('ss'):
            query = query[:-1]
            
        if query == 'ring':
            jewellery = jewellery.filter(Q(type='ring') | (Q(name__icontains='ring') & ~Q(type='earring')))
        elif query == 'earring':
             jewellery = jewellery.filter(type='earring')
        else:
            jewellery = jewellery.filter(Q(name__icontains=search_query) | Q(type__icontains=query))

    all_types = [t[0] for t in Jewellery.TYPE_CHOICES]
    all_materials = [m[0] for m in Jewellery.MATERIAL_CHOICES]

    # Limit to latest 12 on home page
    jewellery = jewellery.order_by('-id')[:12]

    context = get_common_context(request)
    context.update({
        'banners': banners,
        'jewellery': jewellery,
        'all_types': all_types,
        'all_materials': all_materials,
        'all_karats': Jewellery.objects.values_list('karat', flat=True).distinct(),
        'selected_types': selected_types,
        'selected_karats': selected_karats,
        'selected_materials': selected_materials,
    })

    return render(request, 'home.html', context)

def about(request):
    banners = Banner.objects.filter(page='about', is_active=True)
    context = get_common_context(request)
    context['banners'] = banners
    return render(request,"about.html", context)

def privacy(request):
    return render(request,"privacy.html", get_common_context(request))

def terms(request):
    return render(request,"terms.html", get_common_context(request))

def craftsmanship(request):
    return render(request,"craftsmanship.html", get_common_context(request))

def promises(request):
    return render(request,"promises.html", get_common_context(request))

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        subject = f"New Inquiry from {name}"
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        
        try:
            send_mail(
                subject,
                body,
                settings.EMAIL_HOST_USER,  # From
                [settings.EMAIL_HOST_USER], # To (Admin)
                fail_silently=False,
            )
            messages.success(request, "Your message has been sent successfully! We will get back to you soon.")
        except Exception as e:
            messages.error(request, f"Error sending message: {e}")
            
        return redirect('contact')

    banners = Banner.objects.filter(page='contact', is_active=True)
    context = get_common_context(request)
    context.update({'banners': banners})
    return render(request, 'contact.html', context)

def logout_view(request):
    messages.success(request, "Farewell | Until your next discovery", extra_tags='logout-popup')
    # Use pop instead of flush to avoid logging out staff/admin
    request.session.pop("user_id", None)
    request.session.pop("first_name", None)
    return redirect("home")

def profile_view(request):
    user = get_current_user(request)
    if not user:
        return redirect('login')
    
    context = get_common_context(request)
    context['user_profile'] = user
    context['edit_mode'] = False
    return render(request, 'profile.html', context)

def edit_profile(request):
    user = get_current_user(request)
    if not user:
        return redirect('login')
        
    if request.method == "POST":
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.address = request.POST.get('address', user.address)
        user.save()
        
        # update session name if changed
        request.session['first_name'] = user.first_name
        
        messages.success(request, "Profile updated successfully!")
        return redirect('profile_view')
        
    context = get_common_context(request)
    context['user_profile'] = user
    context['edit_mode'] = True
    return render(request, 'profile.html', context)

def auth_view(request):
    # ================= REGISTER =================
    if request.method == "POST" and request.POST.get("form_type") == "register":

        first_name = request.POST.get("first_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Password match check
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("login")

        # Email already exists
        if RegisterUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("login")

        # Save user safely
        new_user = RegisterUser.objects.create(
            first_name=first_name,
            email=email,
            password=password   # (later hash karna)
        )

        # -------- SEND EMAIL --------
        try:
            send_welcome_email(new_user)
        except Exception as e:
            messages.warning(request, f"Registration successful, but email failed: {e}")

        # Success message
        messages.success(request, f"Welcome to the Legacy, {first_name} | Account Confirmed", extra_tags='register-success')
        return redirect("login")

    # -------- LOGIN --------
    if request.method == "POST" and request.POST.get("email"):
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Check if this is a staff member first
        try:
            staff = StaffUser.objects.get(email=email, password=password, is_active=True)
            request.session['staff_id'] = staff.id
            request.session['staff_name'] = staff.name
            request.session['staff_role'] = staff.role
            messages.success(request, f"Login Successful! Welcome, {staff.name}!")
            return redirect('staff_dashboard')
        except StaffUser.DoesNotExist:
            pass  # Not a staff user, check customer login below

        try:
            user = RegisterUser.objects.get(email=email, password=password)
            request.session["first_name"] = user.first_name
            request.session["user_id"] = user.id
            
            # ... Transfer session cart/wishlist to user ...
            session_id = request.session.session_key
            if session_id:
                CartItem.objects.filter(session_id=session_id, user__isnull=True).update(user=user, session_id=None)
                WishlistItem.objects.filter(session_id=session_id, user__isnull=True).update(user=user, session_id=None)

            messages.success(request, f"Login Successful! Welcome Back, {user.first_name} | Essence of Purity", extra_tags='login-popup')
            return redirect("home")
        except RegisterUser.DoesNotExist:
            messages.error(request, "Invalid email or password")
            return redirect("login")

    return render(request, "login.html")

def jewellery_detail(request, name):
    jewellery = get_object_or_404(Jewellery, name=name)
    jewellery.views_count += 1
    jewellery.save()

    base_price = jewellery.current_price
    settings = SiteSetting.objects.first()
    from decimal import Decimal
    making_percent = settings.active_making_charge_percent if settings else Decimal('3.00')
    making_charges = base_price * (making_percent / Decimal('100.00'))
    gst_amount = (base_price + making_charges) * Decimal('0.05')
    total_price = base_price + making_charges + gst_amount
    
    reviews = ProductReview.objects.filter(jewellery=jewellery).order_by('-created_at')
    
    # Calculate average rating
    avg_rating = 0
    if reviews.exists():
        avg_rating = sum([r.rating for r in reviews]) / reviews.count()

    related_products = Jewellery.objects.filter(type=jewellery.type).exclude(id=jewellery.id).order_by('?')[:4]

    context = get_common_context(request)
    context.update({
        'jewellery': jewellery,
        'making_percent': making_percent,
        'making_charges': making_charges,
        'gst_amount': gst_amount,
        'total_price': total_price,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'related_products': related_products
    })
    return render(request, "jewellery_detail.html", context)

def submit_review(request, jewellery_id):
    if request.method == 'POST':
        user = get_current_user(request)
        if not user:
            messages.warning(request, "Please login to submit a review.")
            return redirect(request.META.get('HTTP_REFERER', 'home'))
            
        jewellery = get_object_or_404(Jewellery, id=jewellery_id)
        rating = int(request.POST.get('rating', 5))
        review_text = request.POST.get('review_text', '')
        
        ProductReview.objects.create(
            jewellery=jewellery,
            user=user,
            rating=rating,
            review_text=review_text
        )
        
        messages.success(request, "Thank you! Your review has been submitted.")
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def metal_price_api(request):
    latest_price = MetalPrice.objects.last()
    site_setting = SiteSetting.objects.first()
    api_key = site_setting.goldapi_key if site_setting else None
    
    # Update if older than 4 hours to avoid API rate limit (free tier offers 500/mo)
    time_threshold = timezone.now() - timedelta(hours=4)
    should_update = not latest_price or latest_price.updated_at < time_threshold

    error_msg = None

    if api_key and should_update:
        try:
            headers = {
                "x-access-token": api_key,
                "Content-Type": "application/json"
            }
            # Fetch Gold API and Silver API 
            gold_res = requests.get("https://www.goldapi.io/api/XAU/INR", headers=headers, timeout=5)
            silver_res = requests.get("https://www.goldapi.io/api/XAG/INR", headers=headers, timeout=5)
            
            if gold_res.status_code == 200 and silver_res.status_code == 200:
                gold_data = gold_res.json()
                silver_data = silver_res.json()
                
                new_gold = Decimal(str(gold_data.get('price_gram_24k', 0)))
                new_silver = Decimal(str(silver_data.get('price_gram_24k', 0)))
                
                if new_gold > 0 and new_silver > 0:
                    # Append new price if changed to keep history
                    if not latest_price or latest_price.gold_price != new_gold or latest_price.silver_price != new_silver:
                        latest_price = MetalPrice.objects.create(
                            gold_price=new_gold,
                            silver_price=new_silver
                        )
                    else:
                        latest_price.save() # update timestamp so it doesn't refetch soon
            else:
                error_msg = f"API error: Gold {gold_res.status_code}, Silver {silver_res.status_code}"
        except Exception as e:
            error_msg = str(e)
            print(f"API Error: {e}")

    if not latest_price:
        return JsonResponse({
            "gold": None,
            "silver": None,
            "error": error_msg
        })

    return JsonResponse({
        "gold": float(latest_price.gold_price),
        "silver": float(latest_price.silver_price),
        "updated_at": latest_price.updated_at.strftime("%d %b %Y %I:%M %p")
    })

# --- CART VIEWS ---

def cart_view(request):
    user = get_current_user(request)
    if not user:
        messages.info(request, "Please login to view your cart.")
        return redirect("login")

    cart_items = CartItem.objects.filter(user=user)
    base_total = sum(item.subtotal for item in cart_items)
    
    settings = SiteSetting.objects.first()
    making_percent = settings.active_making_charge_percent if settings else Decimal('3.00')
    
    making_charges = base_total * (making_percent / Decimal('100.00'))
    
    gst_amount = (base_total + making_charges) * Decimal('0.05')
    total_price = base_total + making_charges + gst_amount
    
    context = get_common_context(request)
    context.update({
        "cart_items": cart_items,
        "base_total": base_total,
        "making_percent": making_percent,
        "making_charges": making_charges,
        "gst_amount": gst_amount,
        "total_price": total_price,
    })
    return render(request, "cart.html", context)

def catalog_view(request):
    search_query = request.GET.get('search', '').strip()
    selected_types = request.GET.getlist('type')
    selected_categories = request.GET.getlist('category')
    selected_karats = request.GET.getlist('karat')
    selected_materials = request.GET.getlist('material')
    in_stock_only = request.GET.get('in_stock') == 'true'

    jewellery = Jewellery.objects.all().order_by('-id')
    
    if selected_types:
        jewellery = jewellery.filter(type__in=selected_types)
    elif request.GET.get('type'): # Handle single choice from catalog chips
         jewellery = jewellery.filter(type=request.GET.get('type'))

    if selected_categories:
        jewellery = jewellery.filter(category__name__in=selected_categories)
    elif request.GET.get('category'):
         jewellery = jewellery.filter(category_id=request.GET.get('category'))
         
    if selected_karats:
        jewellery = jewellery.filter(karat__in=selected_karats)
    if selected_materials:
        jewellery = jewellery.filter(material_type__in=selected_materials)
    
    if in_stock_only:
        jewellery = jewellery.filter(is_in_stock=True)
    
    if search_query:
        query = search_query.lower().strip()
        # Accuracy fix: If searching for 'ring', don't show 'earrings'
        if query == 'ring' or query == 'rings':
            jewellery = jewellery.filter(Q(type='ring') | (Q(name__icontains='ring') & ~Q(type='earring')))
        elif query == 'earring' or query == 'earrings':
             jewellery = jewellery.filter(type='earring')
        else:
            jewellery = jewellery.filter(name__icontains=search_query)
        
    context = get_common_context(request)
    context.update({
        'jewellery': jewellery,
        'all_types': Jewellery.TYPE_CHOICES,
        'all_materials': [m[0] for m in Jewellery.MATERIAL_CHOICES],
        'selected_karats': selected_karats,
        'selected_materials': selected_materials,
        'active_page': 'catalog',
    })
    return render(request, 'catalog.html', context)

def add_to_cart(request, jewellery_id):
    user = get_current_user(request)
    if not user:
        messages.warning(request, "Please login to add items to your cart.")
        return redirect("login")

    jewellery = get_object_or_404(Jewellery, id=jewellery_id)
    
    if not jewellery.is_in_stock or jewellery.stock_quantity <= 0:
        messages.error(request, "This item is out of stock. You can save it to your wishlist.")
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    quantity = int(request.POST.get('quantity', 1) if request.method == 'POST' else request.GET.get('quantity', 1))
    
    cart_item, created = CartItem.objects.get_or_create(user=user, jewellery=jewellery)
        
    if not created:
        if cart_item.quantity + quantity > jewellery.stock_quantity:
            messages.warning(request, f"You cannot add more than available stock ({jewellery.stock_quantity}).")
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        cart_item.quantity += quantity
    else:
        if quantity > jewellery.stock_quantity:
            messages.warning(request, f"You cannot add more than available stock ({jewellery.stock_quantity}).")
            cart_item.delete()
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        cart_item.quantity = quantity
    
    cart_item.save()

    # Sync with wishlist
    WishlistItem.objects.filter(user=user, jewellery=jewellery).update(moved_to_cart=True)
        
    messages.success(request, f"{quantity} x {jewellery.name} added to cart.")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        session_id = get_session_id(request)
        if user:
            cart_count = CartItem.objects.filter(user=user).aggregate(Sum('quantity'))['quantity__sum'] or 0
        else:
            cart_count = CartItem.objects.filter(session_id=session_id).aggregate(Sum('quantity'))['quantity__sum'] or 0
            
        return JsonResponse({
            "status": "success",
            "message": f"{quantity} x {jewellery.name} added to cart.",
            "cart_count": cart_count
        })
        
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def remove_from_cart(request, item_id):
    user = get_current_user(request)
    cart_item = get_object_or_404(CartItem, id=item_id)
    jewellery = cart_item.jewellery
    cart_item.delete()

    # If it was in wishlist, mark as not moved_to_cart so it reappears
    if user:
        WishlistItem.objects.filter(user=user, jewellery=jewellery).update(moved_to_cart=False)

    messages.info(request, "Item removed from cart.")
    return redirect("cart_view")

def update_cart_quantity(request, item_id, action):
    cart_item = get_object_or_404(CartItem, id=item_id)
    
    if action == 'plus':
        if cart_item.quantity < cart_item.jewellery.stock_quantity:
            cart_item.quantity += 1
        else:
            messages.warning(request, f"Maximum available stock ({cart_item.jewellery.stock_quantity}) reached.")
            return redirect("cart_view")
    elif action == 'minus':
        if cart_item.quantity > 1:
             cart_item.quantity -= 1
        else:
            messages.info(request, "Minimum quantity reached. Use the remove button to delete the item.")
            return redirect("cart_view")
            
    cart_item.save()
    return redirect("cart_view")

# --- WISHLIST VIEWS ---

def wishlist_view(request):
    user = get_current_user(request)
    if not user:
        messages.info(request, "Please login to view your wishlist.")
        return redirect("login")
        
    # Only show items not currently in cart
    wishlist_items = WishlistItem.objects.filter(user=user, moved_to_cart=False)
        
    context = get_common_context(request)
    context["wishlist_items"] = wishlist_items
    return render(request, "wishlist.html", context)

def add_to_wishlist(request, jewellery_id):
    user = get_current_user(request)
    if not user:
        messages.warning(request, "Please login to add items to your wishlist.")
        return redirect("login")

    jewellery = get_object_or_404(Jewellery, id=jewellery_id)
    WishlistItem.objects.get_or_create(user=user, jewellery=jewellery)
        
    messages.success(request, f"{jewellery.name} added to wishlist.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def remove_from_wishlist(request, item_id):
    wishlist_item = get_object_or_404(WishlistItem, id=item_id)
    wishlist_item.delete()
    messages.info(request, "Item removed from wishlist.")
    return redirect("wishlist_view")

def toggle_wishlist(request, jewellery_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Please login first"}, status=401)

    jewellery = get_object_or_404(Jewellery, id=jewellery_id)
    wishlist_item = WishlistItem.objects.filter(user=user, jewellery=jewellery).first()

    if wishlist_item:
        wishlist_item.delete()
        action = "removed"
        messages.info(request, f"{jewellery.name} removed from wishlist.")
    else:
        WishlistItem.objects.create(user=user, jewellery=jewellery)
        action = "added"
        messages.success(request, f"{jewellery.name} added to wishlist.")

    wishlist_count = WishlistItem.objects.filter(user=user).count()
    return JsonResponse({
        "status": "success",
        "action": action,
        "wishlist_count": wishlist_count
    })

def subscribe_newsletter(request):
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            # Check if already subscribed
            subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if created:
                messages.success(request, "Thank you for subscribing to our newsletter!", extra_tags='login-popup')
            else:
                messages.info(request, "You are already subscribed to our newsletter.", extra_tags='login-popup')
        else:
            messages.error(request, "Please provide a valid email address.")
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def process_checkout(request):
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Please login first"}, status=401)
        
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            method = data.get('method')
            
            cart_items = CartItem.objects.filter(user=user)
            if not cart_items.exists():
                return JsonResponse({"status": "error", "message": "Cart is empty."})
                
            base_total = sum(item.subtotal for item in cart_items)
            
            settings = SiteSetting.objects.first()
            making_percent = settings.active_making_charge_percent if settings else Decimal('3.00')
            
            making_charges = base_total * (making_percent / Decimal('100.00'))

            gst_amount = (base_total + making_charges) * Decimal('0.05')
            total_price = base_total + making_charges + gst_amount
            
            # Create Order
            order = Order.objects.create(
                user=user,
                base_amount=base_total,
                making_charges=making_charges,
                discount_amount=Decimal('0.00'),
                gst_amount=gst_amount,
                total_amount=total_price,
                payment_method=method,
                pickup_date=data.get('pickup_date') or None,
                pickup_time=data.get('pickup_time') or None,
                is_paid=True if method == 'online' else False
            )

            order.refresh_from_db()
            
            items_str = ""
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    jewellery=item.jewellery,
                    quantity=item.quantity,
                    price=item.jewellery.current_price
                )
                items_str += f"- {item.quantity}x {item.jewellery.name} (Amount:  RS {item.subtotal})\n"
                
                # Update inventory stock and sales count
                jewellery = item.jewellery
                jewellery.sales_count += item.quantity
                if jewellery.stock_quantity >= item.quantity:
                    jewellery.stock_quantity -= item.quantity
                else:
                    jewellery.stock_quantity = 0
                jewellery.save()
                
            # Clear target cart
            cart_items.delete()
            
            # Send Professional HTML Email with PDF
            order_items = list(order.items.select_related('jewellery').all())
            try:
                send_order_email(order, order_items, user)
            except Exception as e:
                print(f"ORDER EMAIL ERROR: {e}")
                import traceback
                traceback.print_exc()
            
            return JsonResponse({"status": "success", "order_id": order.id})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Ensure a user is seeing their own order securely
    # if order.user != get_current_user(request):
    #     pass # For production, restrict this. Currently trusting logged in user.
    
    settings = SiteSetting.objects.first()
    making_percent = settings.active_making_charge_percent if settings else 3
    
    context = get_common_context(request)
    context['order'] = order
    context['making_percent'] = making_percent
    return render(request, "order_success.html", context)

def order_history(request):
    user = get_current_user(request)
    if not user:
        return redirect('login')
        
    orders = Order.objects.filter(user=user).order_by('-order_date').prefetch_related('items__jewellery')
    
    context = get_common_context(request)
    context['orders'] = orders
    return render(request, "order_history.html", context)


def download_invoice(request, order_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Please login first.")
        return redirect('login')
        
    order = get_object_or_404(Order, id=order_id, user=user)
    items = list(order.items.select_related('jewellery').all())
    
    pdf_content = generate_order_pdf(order, items, user)
    if not pdf_content:
        messages.error(request, "Error generating PDF. Please try again later.")
        return redirect('order_history')
        
    doc_type = "Voucher" if order.payment_method == 'pay_at_shop' else "Invoice"
    filename = f"Triratna_Order_{order.id}_{doc_type}.pdf"
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ============== CANCEL ORDER ==============
def cancel_order_form(request):
    """Show cancel order form - enter order number and email."""
    user = get_current_user(request)
    context = get_common_context(request)
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id', '').strip()
        email = request.POST.get('email', '').strip()
        
        # Security: If user is logged in, they MUST use their own email
        if user and email != user.email:
            messages.error(request, "Security Alert: You can only cancel orders associated with your account.")
            return redirect('cancel_order_form')
            
        try:
            order_id = int(order_id)
            # Find order ensuring it belongs to the email provided (and verified against session if logged in)
            order = Order.objects.get(id=order_id, user__email=email)
            
            # Only online payment orders can be cancelled
            if order.payment_method != 'online':
                messages.error(request, "Only online payment orders can be cancelled. Pay at Shop orders cannot be cancelled online.")
                return redirect('cancel_order_form')
            
            return redirect('cancel_order_confirm', order_id=order.id, email=email)
            
        except (ValueError, Order.DoesNotExist):
            messages.error(request, "Order not found. Please check your Order Number and Email.")
            return redirect('cancel_order_form')
    
    return render(request, "cancel_order_form.html", context)


def cancel_order_confirm(request, order_id, email):
    """Show order details with cancel button and refund calculation."""
    from django.utils import timezone
    user = get_current_user(request)
    context = get_common_context(request)
    
    # Security: Verify email against session if logged in
    if user and email != user.email:
        messages.error(request, "Unauthorized access to order details.")
        return redirect('cancel_order_form')
        
    try:
        order = Order.objects.get(id=order_id, user__email=email)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('cancel_order_form')
    
    # Only online payment
    if order.payment_method != 'online':
        messages.error(request, "Only online payment orders can be cancelled.")
        return redirect('cancel_order_form')
    
    # Calculate time difference
    now = timezone.now()
    time_diff = now - order.order_date
    hours_passed = time_diff.total_seconds() / 3600
    
    # Refund policy
    if hours_passed <= 24:
        charge_percent = Decimal('0')
        refund_status = 'full'
        refund_message = '100% Refund (Within 24 hours)'
    elif hours_passed <= 48:
        charge_percent = Decimal('1')
        refund_status = 'partial'
        refund_message = '99% Refund (1% cancellation charge after 24 hours)'
    else:
        charge_percent = Decimal('100')
        refund_status = 'none'
        refund_message = 'No refund available (Order is older than 48 hours)'
    
    cancellation_charge = (order.total_amount * charge_percent) / Decimal('100')
    refund_amount = order.total_amount - cancellation_charge
    
    items = order.items.all()
    
    context.update({
        'order': order,
        'items': items,
        'hours_passed': round(hours_passed, 1),
        'charge_percent': charge_percent,
        'cancellation_charge': cancellation_charge,
        'refund_amount': refund_amount,
        'refund_status': refund_status,
        'refund_message': refund_message,
        'email': email,
    })
    return render(request, "cancel_order_confirm.html", context)


def cancel_order_process(request, order_id):
    """Process the actual cancellation."""
    from django.utils import timezone
    user = get_current_user(request)
    
    if request.method != 'POST':
        return redirect('cancel_order_form')
    
    email = request.POST.get('email', '')
    
    # Security: Verify email against session if logged in
    if user and email != user.email:
        messages.error(request, "Unauthorized cancellation attempt.")
        return redirect('cancel_order_form')
        
    try:
        order = Order.objects.get(id=order_id, user__email=email)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('cancel_order_form')
    
    if order.payment_method != 'online':
        messages.error(request, "Only online payment orders can be cancelled.")
        return redirect('cancel_order_form')
    
    # Calculate refund
    now = timezone.now()
    time_diff = now - order.order_date
    hours_passed = time_diff.total_seconds() / 3600
    
    if hours_passed <= 24:
        charge_percent = Decimal('0')
    elif hours_passed <= 48:
        charge_percent = Decimal('1')
    else:
        messages.error(request, "No refund available. Order is older than 48 hours.")
        return redirect('cancel_order_form')
    
    cancellation_charge = (order.total_amount * charge_percent) / Decimal('100')
    refund_amount = order.total_amount - cancellation_charge
    
    # Save items data before deleting
    items_data = []
    for item in order.items.all():
        items_data.append({
            'jewellery_name': item.jewellery.name,
            'jewellery_id': item.jewellery.id,
            'quantity': item.quantity,
            'price': str(item.price),
            'line_total': str(item.line_total),
        })
        # Restore stock quantity
        item.jewellery.stock_quantity += item.quantity
        item.jewellery.sales_count = max(0, item.jewellery.sales_count - item.quantity)
        item.jewellery.save()
    
    # Create CancelledOrder record
    CancelledOrder.objects.create(
        original_order_id=order.id,
        user=order.user,
        base_amount=order.base_amount,
        making_charges=order.making_charges,
        gst_amount=order.gst_amount,
        total_amount=order.total_amount,
        refund_amount=refund_amount,
        charge_percentage=charge_percent,
        payment_method=order.payment_method,
        order_date=order.order_date,
        items_data=items_data,
    )
    
    # Send cancellation email with PDF receipt
    cancelled_obj = CancelledOrder.objects.filter(original_order_id=order.id).order_by('-cancelled_at').first()
    if cancelled_obj:
        try:
            send_cancel_email(cancelled_obj, order.user)
        except Exception:
            pass
    
    # Delete the original order
    order.delete()
    
    messages.success(request, f"Order #{order_id} cancelled successfully! Refund of ₹{refund_amount:.2f} will be processed.")
    return redirect('cancel_order_success')


def cancel_order_success(request):
    """Show cancellation success page."""
    context = get_common_context(request)
    return render(request, "cancel_order_success.html", context)
