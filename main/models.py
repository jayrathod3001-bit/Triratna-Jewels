from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

class Banner(models.Model):
    PAGE_CHOICES = (
        ('home', 'Home Page'),
        ('about', 'About Page'),
        ('contact', 'Contact Page'),
    )
    image = models.ImageField(upload_to='banners/')
    page = models.CharField(
        max_length=20,
        choices=PAGE_CHOICES,
        default='home'
    )
    heading = models.CharField(max_length=200,blank=True, null=True)
    subheading = models.CharField(max_length=300,blank=True, null=True)
    button_text = models.CharField(max_length=50,blank=True, null=True)
    button_link = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.page.upper()} Banner #{self.id}"


class Jewellery(models.Model):
    
    MATERIAL_CHOICES = [
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
        ('ruby', 'Ruby'),
        ('emerald', 'Emerald'),
        ('others', 'Others'),
    ]
    material_type = models.CharField(max_length=20, choices=MATERIAL_CHOICES, default='gold')
    
    TYPE_CHOICES = [
        ('ring', 'Ring'),
        ('necklace', 'Necklace'),
        ('earring', 'Earring'),
        ('bracelet', 'Bracelet'),
        ('bangles','Bangles'),
        ('payal','payal')
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='ring')
    
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='jewellery/')

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        help_text="Weight in grams (Use Carats for Diamond/Ruby weight equivalent in grams)"
    )

    karat = models.CharField(
        max_length=10,
        choices=[
            ('22K', '22 Karat'),
            ('24K', '24 Karat'),
            ('NA', 'Not Applicable')
        ],
        default='22K'
    )

    manual_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        help_text="Rate per gram (Applicable for non-gold/silver items)"
    )

    price = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    stock_quantity = models.PositiveIntegerField(default=1)
    is_in_stock = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    is_recommended = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True, help_text="Story and craftsmanship details for the editorial section")
    views_count = models.PositiveIntegerField(default=0)
    sales_count = models.PositiveIntegerField(default=0)

    @property
    def current_price(self):
        from decimal import Decimal
        rate = Decimal('0.00')
        
        if self.material_type == 'gold':
            latest_rates = MetalPrice.objects.last()
            if latest_rates:
                rate = latest_rates.gold_price
                if self.karat == '22K':
                    rate = rate * Decimal('0.92')
        elif self.material_type == 'silver':
            latest_rates = MetalPrice.objects.last()
            if latest_rates:
                rate = latest_rates.silver_price
        else:
            rate = self.manual_rate

        return self.weight * rate

    def save(self, *args, **kwargs):
        # Auto-update in_stock based on quantity
        if self.stock_quantity <= 0:
            self.is_in_stock = False
        else:
            self.is_in_stock = True
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({'In Stock' if self.is_in_stock else 'Out of Stock'})"

class RegisterUser(models.Model):
    first_name = models.CharField(max_length=100,blank=True, null=True)
    last_name = models.CharField(max_length=100,blank=True, null=True)
    phone_number = models.CharField(max_length=15,blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.first_name
    
class MetalPrice(models.Model):
    gold_price = models.DecimalField(max_digits=10, decimal_places=2)
    silver_price = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Gold: {self.gold_price} | Silver: {self.silver_price}"

class CartItem(models.Model):
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    jewellery = models.ForeignKey(Jewellery, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return self.jewellery.current_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.jewellery.name}"

class WishlistItem(models.Model):
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    jewellery = models.ForeignKey(Jewellery, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    moved_to_cart = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'jewellery', 'session_id')

    def __str__(self):
        return f"{self.jewellery.name} in wishlist"

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

@receiver(post_save, sender=MetalPrice)
def send_metal_price_update(sender, instance, created, **kwargs):
    subscribers = NewsletterSubscriber.objects.all()
    recipient_list = [s.email for s in subscribers]
    
    if recipient_list:
        try:
            from .email_utils import send_metal_price_email
            send_metal_price_email(recipient_list, instance.gold_price, instance.silver_price)
        except Exception as e:
            print(f"Error sending newsletter: {e}")

class SiteSetting(models.Model):
    whatsapp_number = models.CharField(max_length=20, help_text="Enter WhatsApp number with country code (e.g., 919876543210)", default="910000000000")
    goldapi_key = models.CharField(max_length=100, blank=True, null=True, help_text="Get your free API key from goldapi.io")
    active_making_charge_percent = models.DecimalField(max_digits=5, decimal_places=2, default=3, help_text="Set the making charge percentage for the entire site (default is 3.00)")
    
    def __str__(self):
        return "Site Settings"


class Order(models.Model):
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    making_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50) # 'pay_at_shop' or 'online'
    pickup_date = models.DateField(null=True, blank=True)
    pickup_time = models.TimeField(null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
        
    def __str__(self):
        return f"Order #{self.id} by {self.user.first_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    jewellery = models.ForeignKey(Jewellery, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    
    @property
    def line_total(self):
        return self.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.jewellery.name}"

class StaffUser(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('sales', 'Sales Staff'),
        ('inventory', 'Inventory Staff'),
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='sales')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

class CancelledOrder(models.Model):
    original_order_id = models.IntegerField()
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    making_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    cancellation_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50)
    order_date = models.DateTimeField()
    cancelled_at = models.DateTimeField(auto_now_add=True)
    items_data = models.JSONField(default=list)
    reason = models.CharField(max_length=255, default='Customer requested cancellation')

    def __str__(self):
        return f"Cancelled Order #{self.original_order_id} by {self.user.first_name}"

class ProductReview(models.Model):
    jewellery = models.ForeignKey(Jewellery, on_delete=models.CASCADE)
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.first_name} on {self.jewellery.name}"
