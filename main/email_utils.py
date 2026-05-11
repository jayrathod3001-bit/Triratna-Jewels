"""
Email utility functions for Triratna Jewels.
Professional HTML email templates with PDF attachments.
"""
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from io import BytesIO
from datetime import datetime


def get_email_header():
    return '''
    <div style="background-color: #1a1a1a; padding: 45px 20px; text-align: center; border-bottom: 3px solid #d4af37;">
        <h1 style="color: #d4af37; font-size: 26px; margin: 0; letter-spacing: 6px; font-family: 'Times New Roman', Times, serif; font-weight: normal; text-transform: uppercase;">TRIRATNA JEWELS</h1>
        <p style="color: rgba(212, 175, 55, 0.6); font-size: 10px; margin-top: 10px; letter-spacing: 3px; text-transform: uppercase;">Where Purity Finds Form</p>
    </div>
    '''


def get_email_footer():
    return '''
    <div style="background-color: #1a1a1a; padding: 35px 20px; text-align: center; color: #ffffff;">
        <p style="color: #d4af37; font-weight: bold; font-size: 13px; margin: 0 0 10px; letter-spacing: 2px; text-transform: uppercase;">The Boutique Experience</p>
        <p style="color: rgba(255,255,255,0.5); font-size: 11px; margin: 0 0 15px; font-family: 'Georgia', serif; font-style: italic;">"Crafting legacies, one masterpiece at a time."</p>
        <div style="height: 1px; width: 40px; background: #d4af37; margin: 0 auto 15px;"></div>
        <p style="color: rgba(255,255,255,0.3); font-size: 10px; margin: 0;">© 2026 Triratna Jewels. All Rights Reserved.</p>
        <p style="color: rgba(255,255,255,0.2); font-size: 9px; margin-top: 5px;">This is an automated correspondence from Triratna. Please do not reply.</p>
    </div>
    '''


def build_html_email(title, body_content):
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: 'Georgia', serif;">
    <div style="max-width: 600px; margin: 40px auto; background-color: #ffffff; border: 1px solid #e0e0e0; overflow: hidden;">
        {get_email_header()}
        <div style="padding: 40px 30px; background-color: #fdfcf8;">
            <h2 style="color: #1a1a1a; font-size: 22px; margin: 0 0 25px; text-align: center; font-family: 'Times New Roman', Times, serif; font-weight: normal; text-transform: uppercase; letter-spacing: 2px;">{title}</h2>
            {body_content}
        </div>
        {get_email_footer()}
    </div>
    </body>
    </html>
    '''


def send_html_email(subject, html_content, to_email, attachments=None):
    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[to_email] if isinstance(to_email, str) else to_email,
    )
    email.content_subtype = 'html'
    
    if attachments:
        for name, content, mime in attachments:
            email.attach(name, content, mime)
    
    email.send(fail_silently=False)


def generate_order_pdf(order, items, user):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
    except ImportError:
        return None
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Main Background - Warm Cream/White
    c.setFillColor(HexColor('#ffffff'))
    c.rect(0, 0, width, height, fill=True, stroke=False)
    
    # Decorative Gold Corner Ornaments
    c.setStrokeColor(HexColor('#d4af37'))
    c.setLineWidth(0.5)
    # Top Corners
    c.line(15, height-15, 55, height-15)
    c.line(15, height-15, 15, height-55)
    c.line(width-15, height-15, width-55, height-15)
    c.line(width-15, height-15, width-15, height-55)
    # Bottom Corners
    c.line(15, 15, 55, 15)
    c.line(15, 15, 15, 55)
    c.line(width-15, 15, width-55, 15)
    c.line(width-15, 15, width-15, 55)

    # Center Watermark - Faint & Elegant
    c.saveState()
    c.setFont("Times-Bold", 60)
    c.setFillColor(HexColor('#d4af37'), alpha=0.03)
    c.translate(width/2, height/2)
    c.rotate(45)
    c.drawCentredString(0, 0, "TRIRATNA JEWELS")
    c.restoreState()

    # Header Section - Bright Gold Band
    c.setFillColor(HexColor('#fffcf0'))
    c.rect(20, height - 85, width - 40, 65, fill=True, stroke=True)
    
    c.setFillColor(HexColor('#d4af37'))
    c.setFont("Times-Bold", 32)
    c.drawCentredString(width / 2, height - 52, "TRIRATNA JEWELS")
    
    c.setFillColor(HexColor('#8e6d51'))
    c.setFont("Times-Italic", 9)
    c.drawCentredString(width / 2, height - 70, "WHERE PURITY FINDS FORM  |  SINCE GENERATIONS")
    
    # Compact Document Title
    is_voucher = order.payment_method == 'pay_at_shop'
    doc_title = "PAY AT SHOP VOUCHER" if is_voucher else "ORDER INVOICE"
    c.setFillColor(HexColor('#d4af37'))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 105, doc_title)
    
    # Compact Order Details
    y = height - 130
    c.setStrokeColor(HexColor('#d4af37'))
    c.setLineWidth(0.5)
    c.line(40, y, width - 40, y)
    
    y -= 20
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor('#333333'))
    c.drawString(50, y, f"ORDER: #{order.id}")
    c.drawRightString(width - 50, y, f"DATE: {order.order_date.strftime('%d %b %Y')}")
    
    y -= 15
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#555555'))
    c.drawString(50, y, f"CLIENT: {user.first_name} {user.last_name or ''}")
    payment_text = "Method: Pay at Shop" if is_voucher else "Method: Online Payment"
    c.drawRightString(width - 50, y, payment_text)
    
    y -= 15
    c.drawString(50, y, f"Email: {user.email}")
    payment_status = "Status: Reservation" if is_voucher else "Status: Paid"
    c.drawRightString(width - 50, y, payment_status)
    
    y -= 15
    c.drawString(50, y, f"Phone: {user.phone_number or 'N/A'}")
    if order.pickup_date:
        c.drawRightString(width - 50, y, f"Pickup: {order.pickup_date.strftime('%d %b %Y')}")
    
    y -= 15
    address_str = (user.address or "Address: N/A").replace('\n', ' ').strip()
    c.drawString(50, y, f"Address: {address_str[:60]}")
    if order.pickup_time:
        c.drawRightString(width - 50, y, f"Time: {order.pickup_time.strftime('%I:%M %p')}")
    
    # Table Header - Compact & Gold
    y -= 30
    c.setFillColor(HexColor('#d4af37'))
    c.rect(40, y - 5, width - 80, 20, fill=True, stroke=False)
    
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "COLLECTION ITEM")
    c.drawCentredString(350, y, "QTY")
    c.drawCentredString(420, y, "RATE")
    c.drawRightString(width - 50, y, "TOTAL")
    
    # Items - Reduced Spacing
    y -= 22
    c.setFillColor(HexColor('#333333'))
    c.setFont("Helvetica", 9)
    
    for item in items:
        c.drawString(50, y, str(item.jewellery.name)[:50])
        c.drawCentredString(350, y, str(item.quantity))
        c.drawCentredString(420, y, f"Rs {item.price:,.2f}")
        c.drawRightString(width - 50, y, f"Rs {item.line_total:,.2f}")
        y -= 15
        c.setStrokeColor(HexColor('#f0f0f0'))
        c.line(50, y + 5, width - 50, y + 5)
    
    # Price Breakdown
    # Price Summary - Compact
    y -= 15
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#666666'))
    c.drawString(350, y, "Subtotal:")
    c.drawRightString(width - 50, y, f"Rs {order.base_amount:,.2f}")
    y -= 12
    c.drawString(350, y, "Artistry (3%):")
    c.drawRightString(width - 50, y, f"Rs {order.making_charges:,.2f}")
    y -= 12
    c.drawString(350, y, "GST (5%):")
    c.drawRightString(width - 50, y, f"Rs {order.gst_amount:,.2f}")
    
    y -= 22
    c.setFillColor(HexColor('#fffcf0'))
    c.rect(340, y - 8, width - 390, 25, fill=True, stroke=True)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor('#d4af37'))
    c.drawString(350, y, "GRAND TOTAL:")
    c.drawRightString(width - 50, y, f"Rs {order.total_amount:,.2f}")
    
    # Conditional Terms based on Payment Method
    if is_voucher:
        terms_title = "ESSENTIAL VOUCHER TERMS:"
        pickup_date_str = order.pickup_date.strftime('%d %b %Y') if order.pickup_date else 'the pickup date'
        terms = [
            f"• This is a RESERVATION VOUCHER only. Final bill depends on gold rates on {pickup_date_str}.",
            "• THE QUANTITY OF ITEMS IS FIXED as per this voucher and cannot be modified at the shop.",
            "• Cancellations: 100% refund within 24 hours, 99% within 48 hours. No refunds after 48 hours.",
            "• Please carry a digital or printed copy of this voucher for verification during pickup.",
            "• Your data is protected under the Triratna Privacy Standard. Visit triratnajewels.com for details."
        ]
    else:
        terms_title = "ESSENTIAL INVOICE TERMS:"
        terms = [
            "• This is a FINAL TAX INVOICE for your online purchase from Triratna Jewels.",
            "• Cancellations: 100% refund within 24 hours, 99% within 48 hours. No refunds after 48 hours.",
            "• Every piece is handcrafted; slight variations reflect its unique artisanal nature.",
            "• Please retain this invoice for your records and for any future service requests.",
            "• We guarantee the authenticity and purity of all materials used in this creation."
        ]

    # The Triratna Promise Section (Spaced Out)
    y -= 55
    c.setFillColor(HexColor('#fffcf0'))
    c.rect(40, y - 60, width - 80, 70, fill=True, stroke=False)
    
    c.setFillColor(HexColor('#d4af37'))
    c.setFont("Times-Bold", 12)
    c.drawCentredString(width/2, y - 5, "THE TRIRATNA PROMISE")
    
    c.setFillColor(HexColor('#8e6d51'))
    c.setFont("Times-Italic", 9.5)
    promise_text = "Every piece of Triratna Jewels is a symbol of Purity, Prosperity, and Promise. Handcrafted by master artisans"
    promise_text2 = "with materials of the highest integrity, we ensure your jewel remains a cherished legacy for generations."
    c.drawCentredString(width/2, y - 25, promise_text)
    c.drawCentredString(width/2, y - 38, promise_text2)
    
    # Bottom Terms & Privacy (Footer Area)
    y_footer = 120
    c.setStrokeColor(HexColor('#d4af37'))
    c.setLineWidth(0.4)
    c.line(40, y_footer, width - 40, y_footer)
    
    c.setFillColor(HexColor('#d4af37'))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(40, y_footer - 18, terms_title)
    
    c.setFillColor(HexColor('#666666'))
    c.setFont("Helvetica", 7.5)
    
    ty = y_footer - 32
    for term in terms:
        c.drawString(40, ty, term)
        ty -= 12

    # Decorative Fleuron at the very bottom
    c.setFillColor(HexColor('#d4af37'))
    c.setFont("Times-Bold", 14)
    c.drawCentredString(width/2, 35, "❦")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def generate_cancel_pdf(cancelled_order, user):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
    except ImportError:
        return None
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Background - Clean
    c.setFillColor(HexColor('#ffffff'))
    c.rect(0, 0, width, height, fill=True, stroke=False)
    
    # Header - Gold Band
    c.setFillColor(HexColor('#fff8f8')) # Light red tint
    c.rect(20, height - 85, width - 40, 65, fill=True, stroke=True)
    
    c.setFillColor(HexColor('#d4af37'))
    c.setFont("Times-Bold", 30)
    c.drawCentredString(width / 2, height - 50, "TRIRATNA JEWELS")
    
    c.setFillColor(HexColor('#c43a3a'))
    c.setFont("Times-Italic", 9)
    c.drawCentredString(width / 2, height - 68, "Order Cancellation Summary")
    
    # Title
    c.setFillColor(HexColor('#c43a3a'))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 105, "CANCELLATION RECEIPT")
    
    y = height - 125
    c.setStrokeColor(HexColor('#c43a3a'))
    c.setLineWidth(0.5)
    c.line(40, y, width - 40, y)
    
    # Details
    y = height - 150
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(HexColor('#333333'))
    c.drawString(50, y, f"Original Order ID: #{cancelled_order.original_order_id}")
    c.drawRightString(width - 50, y, f"Cancelled: {cancelled_order.cancelled_at.strftime('%d %b %Y, %I:%M %p')}")
    
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Customer: {user.first_name} {user.last_name or ''}")
    c.drawRightString(width - 50, y, f"Email: {user.email}")
    
    y -= 15
    c.drawString(50, y, f"Phone: {user.phone_number or 'N/A'}")
    c.drawRightString(width - 50, y, f"Order Date: {cancelled_order.order_date.strftime('%d %b %Y')}")
    
    y -= 15
    address_str = (user.address or "Address: N/A").replace('\n', ' ').strip()
    c.drawString(50, y, f"Address: {address_str[:60]}")
    
    # Items
    y -= 35
    c.setFillColor(HexColor('#dc3545'))
    c.rect(40, y - 5, width - 80, 22, fill=True, stroke=False)
    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "PRODUCT")
    c.drawCentredString(350, y, "QTY")
    c.drawCentredString(420, y, "PRICE")
    c.drawRightString(width - 50, y, "TOTAL")
    
    y -= 25
    c.setFillColor(HexColor('#333333'))
    c.setFont("Helvetica", 10)
    
    for item in cancelled_order.items_data:
        c.drawString(50, y, str(item.get('jewellery_name', ''))[:40])
        c.drawCentredString(350, y, str(item.get('quantity', 0)))
        c.drawCentredString(420, y, f"Rs {float(item.get('price', 0)):,.2f}")
        c.drawRightString(width - 50, y, f"Rs {float(item.get('line_total', 0)):,.2f}")
        y -= 18
    
    # Refund Summary
    y -= 15
    c.setStrokeColor(HexColor('#ead216'))
    c.setLineWidth(2)
    c.line(280, y + 8, width - 50, y + 8)
    
    # Price breakdown
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor('#555555'))
    c.drawString(280, y - 8, "Base Amount:")
    c.drawRightString(width - 50, y - 8, f"Rs {cancelled_order.base_amount:,.2f}")
    
    y -= 18
    c.drawString(280, y - 8, "Making Charges (3%):")
    c.drawRightString(width - 50, y - 8, f"Rs {cancelled_order.making_charges:,.2f}")
    
    y -= 18
    c.drawString(280, y - 8, "GST (5%):")
    c.drawRightString(width - 50, y - 8, f"Rs {cancelled_order.gst_amount:,.2f}")
    
    y -= 20
    c.setFillColor(HexColor('#333333'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(280, y - 8, "Order Total:")
    c.drawRightString(width - 50, y - 8, f"Rs {cancelled_order.total_amount:,.2f}")
    
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(280, y - 8, f"Cancellation Charge ({cancelled_order.charge_percentage}%):")
    c.setFillColor(HexColor('#dc3545'))
    c.drawRightString(width - 50, y - 8, f"- Rs {cancelled_order.cancellation_charge:,.2f}")
    
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor('#28a745'))
    c.drawString(280, y - 8, "REFUND AMOUNT:")
    c.drawRightString(width - 50, y - 8, f"Rs {cancelled_order.refund_amount:,.2f}")
    
    # Footer
    y -= 45
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(HexColor('#888888'))
    c.drawCentredString(width / 2, y, "Refund will be processed within 5-7 business days.")
    c.drawCentredString(width / 2, y - 15, f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ============== EMAIL FUNCTIONS ==============

def send_welcome_email(user):
    body = f'''
    <div style="text-align:center; margin-bottom:30px;">
        <div style="width:50px; height:50px; border:1px solid #d4af37; border-radius:50%; margin:0 auto 20px; line-height:50px;">
            <span style="color:#d4af37; font-size:24px;">✦</span>
        </div>
        <h3 style="color:#1a1a1a; margin:0; font-family:'Times New Roman', serif; font-size:24px; font-weight:normal;">Welcome to Triratna, {user.first_name}</h3>
    </div>
    <p style="color:#444; font-size:15px; line-height:1.8; text-align:center;">
        Your passage to the world of exquisite brilliance has been confirmed. At <strong>Triratna Jewels</strong>, we believe every piece tells a story of heritage and grace.
    </p>
    <div style="background:#fffcf0; border:1px solid #eee; padding:20px; margin:30px 0; text-align:center;">
        <p style="margin:0; font-size:13px; color:#1a1a1a; letter-spacing:1px; text-transform:uppercase;">Membership Profile</p>
        <div style="height:1px; width:30px; background:#d4af37; margin:10px auto;"></div>
        <p style="margin:5px 0 0; font-size:14px; color:#555;"><strong>{user.first_name} {user.last_name or ''}</strong></p>
        <p style="margin:5px 0 0; font-size:13px; color:#888;">{user.email}</p>
    </div>
    <p style="color:#444; font-size:15px; line-height:1.8; text-align:center;">
        Explore our curated collections and begin your journey of prosperity.
    </p>
    <div style="text-align:center; margin-top:35px;">
        <a href="https://triratnajewels.com/catalog/" style="display:inline-block; padding:15px 45px; background-color:#1a1a1a; color:#d4af37; text-decoration:none; letter-spacing:3px; font-size:12px; text-transform:uppercase; font-weight:bold; border: 1px solid #d4af37;">Explore Collection</a>
    </div>
    '''
    html = build_html_email("Membership Confirmed", body)
    send_html_email("Welcome to Triratna Jewels ✦", html, user.email)


def send_order_email(order, items, user):
    is_voucher = order.payment_method == 'pay_at_shop'
    title = "Pay at Shop Voucher" if is_voucher else "Order Invoice"
    
    items_html = ""
    for item in items:
        items_html += f'''
        <tr>
            <td style="padding:10px 12px; border-bottom:1px solid #f0f0f0; font-size:13px;">{item.jewellery.name}</td>
            <td style="padding:10px; border-bottom:1px solid #f0f0f0; text-align:center; font-size:13px;">{item.quantity}</td>
            <td style="padding:10px; border-bottom:1px solid #f0f0f0; text-align:right; font-size:13px;">₹{item.price:,.2f}</td>
            <td style="padding:10px 12px; border-bottom:1px solid #f0f0f0; text-align:right; font-weight:bold; font-size:13px;">₹{item.line_total:,.2f}</td>
        </tr>
        '''
    
    pickup_info = ""
    if order.pickup_date:
        pickup_info = f'''
        <div style="background:#fffcf0; border:1px solid #d4af37; padding:20px; margin:25px 0; text-align:center;">
            <p style="margin:0; font-size:11px; color:#d4af37; text-transform:uppercase; letter-spacing:2px;">Boutique Appointment</p>
            <p style="margin:10px 0 0; font-size:16px; color:#1a1a1a; font-family:'Times New Roman',serif;">{order.pickup_date.strftime('%A, %d %b %Y')}</p>
            {'<p style="margin:5px 0 0; font-size:14px; color:#555;">' + order.pickup_time.strftime('%I:%M %p') + '</p>' if order.pickup_time else ''}
        </div>
        '''
    
    status_text = "PAYMENT PENDING - PAY AT SHOP" if is_voucher else "PAYMENT CONFIRMED"
    
    doc_name = "Voucher" if is_voucher else "Invoice"
    
    body = f'''
    <p style="color:#444; font-size:15px; line-height:1.8;">
        Dear <strong>{user.first_name}</strong>,
    </p>
    <p style="color:#444; font-size:15px; line-height:1.8;">
        We are pleased to acknowledge your recent selection at <strong>Triratna Jewels</strong>. 
        {'Your bespoke reservation voucher has been prepared.' if is_voucher else 'Your online acquisition has been processed successfully.'}
    </p>
    
    <div style="border-top: 1px solid #eee; border-bottom: 1px solid #eee; padding:15px 0; margin:25px 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:1px;">Reference Number</span>
            <span style="font-size:13px; color:#1a1a1a; font-weight:bold;">#{order.id}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:1px;">Date of Transaction</span>
            <span style="font-size:13px; color:#1a1a1a;">{order.order_date.strftime('%d %b %Y')}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:1px;">Status</span>
            <span style="font-size:12px; color:#d4af37; font-weight:bold; letter-spacing:1px;">{status_text}</span>
        </div>
    </div>
    
    {pickup_info}
    
    <table style="width:100%; border-collapse:collapse; margin:25px 0;">
        <thead>
            <tr style="border-bottom: 2px solid #d4af37;">
                <th style="padding:12px 0; text-align:left; color:#1a1a1a; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Selection</th>
                <th style="padding:12px 0; text-align:center; color:#1a1a1a; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Qty</th>
                <th style="padding:12px 0; text-align:right; color:#1a1a1a; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Total</th>
            </tr>
        </thead>
        <tbody>
            {items_html}
        </tbody>
    </table>
    
    <div style="background:#fdfcf8; padding:20px; border:1px solid #eee;">
        <div style="display:flex; justify-content:space-between; padding:5px 0; font-size:13px; color:#666;">
            <span>Base Valuation</span>
            <span>₹{order.base_amount:,.2f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; padding:5px 0; font-size:13px; color:#666;">
            <span>Artistry (3%)</span>
            <span>₹{order.making_charges:,.2f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; padding:5px 0; font-size:13px; color:#666;">
            <span>GST (5%)</span>
            <span>₹{order.gst_amount:,.2f}</span>
        </div>
        <div style="height:1px; background:#d4af37; margin:15px 0;"></div>
        <div style="display:flex; justify-content:space-between; font-size:18px;">
            <span style="font-family:'Times New Roman',serif; color:#1a1a1a; text-transform:uppercase; letter-spacing:1px;">Grand Total</span>
            <span style="font-weight:bold; color:#1a1a1a;">₹{order.total_amount:,.2f}</span>
        </div>
    </div>
    
    <p style="color:#888; font-size:12px; margin-top:30px; font-style:italic; text-align:center;">
        * Detailed terms and privacy guidelines are included in the attached {doc_name}.
    </p>
    '''
    
    html = build_html_email(title, body)
    subject = f"Order #{order.id} {doc_name} - Triratna Jewels ✦"
    
    attachments = []
    pdf_data = generate_order_pdf(order, items, user)
    if pdf_data:
        attachments.append((f"Triratna_Order_{order.id}_{doc_name}.pdf", pdf_data, 'application/pdf'))
    
    send_html_email(subject, html, user.email, attachments)


def send_cancel_email(cancelled_order, user):
    items_html = ""
    for item in cancelled_order.items_data:
        items_html += f'''
        <tr>
            <td style="padding:12px 0; border-bottom:1px solid #eee; font-size:14px; color:#1a1a1a;">{item.get('jewellery_name', '')}</td>
            <td style="padding:12px 0; border-bottom:1px solid #eee; text-align:center; font-size:14px; color:#1a1a1a;">{item.get('quantity', 0)}</td>
            <td style="padding:12px 0; border-bottom:1px solid #eee; text-align:right; font-size:14px; color:#1a1a1a;">₹{float(item.get('line_total', 0)):,.2f}</td>
        </tr>
        '''
    
    body = f'''
    <div style="text-align:center; margin-bottom:30px;">
        <div style="width:50px; height:50px; border:1px solid #c43a3a; border-radius:50%; margin:0 auto 20px; line-height:50px;">
            <span style="color:#c43a3a; font-size:24px;">✕</span>
        </div>
        <h3 style="color:#1a1a1a; margin:0; font-family:'Times New Roman', serif; font-size:22px; font-weight:normal; text-transform:uppercase; letter-spacing:2px;">Cancellation Confirmed</h3>
    </div>
    
    <p style="color:#444; font-size:15px; line-height:1.8; text-align:center;">
        Dear <strong>{user.first_name}</strong>, your request to cancel order <strong>#{cancelled_order.original_order_id}</strong> has been processed.
    </p>
    
    <div style="border: 1px solid #eee; padding:20px; margin:25px 0; background:#fdfcf8;">
        <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
            <span style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:1px;">Original Order</span>
            <span style="font-size:13px; color:#1a1a1a;">#{cancelled_order.original_order_id}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:1px;">Cancelled On</span>
            <span style="font-size:13px; color:#1a1a1a;">{cancelled_order.cancelled_at.strftime('%d %b %Y')}</span>
        </div>
    </div>
    
    <table style="width:100%; border-collapse:collapse; margin:25px 0;">
        <thead>
            <tr style="border-bottom: 2px solid #c43a3a;">
                <th style="padding:12px 0; text-align:left; color:#1a1a1a; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Item</th>
                <th style="padding:12px 0; text-align:center; color:#1a1a1a; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Qty</th>
                <th style="padding:12px 0; text-align:right; color:#1a1a1a; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Amount</th>
            </tr>
        </thead>
        <tbody>
            {items_html}
        </tbody>
    </table>
    
    <div style="background:#fffcf0; padding:20px; border:1px solid #eee;">
        <div style="display:flex; justify-content:space-between; padding:5px 0; font-size:13px; color:#666;">
            <span>Order Total</span>
            <span>₹{cancelled_order.total_amount:,.2f}</span>
        </div>
        <div style="display:flex; justify-content:space-between; padding:5px 0; font-size:13px; color:#c43a3a;">
            <span>Cancellation Fee ({cancelled_order.charge_percentage}%)</span>
            <span>- ₹{cancelled_order.cancellation_charge:,.2f}</span>
        </div>
        <div style="height:1px; background:#d4af37; margin:15px 0;"></div>
        <div style="display:flex; justify-content:space-between; font-size:18px;">
            <span style="font-family:'Times New Roman',serif; color:#1a1a1a; text-transform:uppercase; letter-spacing:1px;">Refund Amount</span>
            <span style="font-weight:bold; color:#1a1a1a;">₹{cancelled_order.refund_amount:,.2f}</span>
        </div>
    </div>
    
    <div style="margin-top:30px; padding:20px; border:1px dashed #d4af37; text-align:center;">
        <p style="margin:0; font-size:13px; color:#1a1a1a; font-family:'Georgia', serif; font-style:italic;">
            "The refund of ₹{cancelled_order.refund_amount:,.2f} will be credited to your original payment method within 5-7 business days."
        </p>
    </div>
    '''
    
    html = build_html_email("Order Cancellation Confirmation", body)
    subject = f"Order #{cancelled_order.original_order_id} Cancelled - Triratna Jewels"
    
    attachments = []
    pdf_data = generate_cancel_pdf(cancelled_order, user)
    if pdf_data:
        attachments.append((f"Triratna_Cancel_Receipt_{cancelled_order.original_order_id}.pdf", pdf_data, 'application/pdf'))
    
    send_html_email(subject, html, user.email, attachments)


def send_metal_price_email(recipient_list, gold_price, silver_price):
    body = f'''
    <div style="text-align:center; margin-bottom:30px;">
        <div style="width:50px; height:50px; border:1px solid #d4af37; border-radius:50%; margin:0 auto 20px; line-height:50px;">
            <span style="color:#d4af37; font-size:22px;">₹</span>
        </div>
        <h3 style="color:#1a1a1a; margin:0; font-family:'Times New Roman', serif; font-size:22px; font-weight:normal; text-transform:uppercase; letter-spacing:2px;">Market Rate Update</h3>
    </div>
    
    <p style="color:#444; font-size:15px; line-height:1.8; text-align:center;">
        Our daily metal valuations have been adjusted. Stay informed with the latest market rates at <strong>Triratna Jewels</strong>.
    </p>
    
    <div style="margin:30px 0; text-align:center;">
        <div style="display:inline-block; width:220px; background:#fffcf0; border:1px solid #d4af37; padding:25px; margin:10px;">
            <p style="margin:0; font-size:11px; color:#d4af37; text-transform:uppercase; letter-spacing:2px;">Gold (24K)</p>
            <p style="margin:15px 0 5px; font-size:24px; color:#1a1a1a; font-family:'Times New Roman',serif;">₹ {gold_price}</p>
            <p style="margin:0; font-size:10px; color:#888;">PER GRAM</p>
        </div>
        <div style="display:inline-block; width:220px; background:#f5f5f5; border:1px solid #ccc; padding:25px; margin:10px;">
            <p style="margin:0; font-size:11px; color:#888; text-transform:uppercase; letter-spacing:2px;">Fine Silver</p>
            <p style="margin:15px 0 5px; font-size:24px; color:#1a1a1a; font-family:'Times New Roman',serif;">₹ {silver_price}</p>
            <p style="margin:0; font-size:10px; color:#888;">PER GRAM</p>
        </div>
    </div>
    
    <div style="text-align:center; margin-top:35px;">
        <a href="https://triratnajewels.com/" style="display:inline-block; padding:15px 45px; background-color:#1a1a1a; color:#d4af37; text-decoration:none; letter-spacing:3px; font-size:11px; text-transform:uppercase; font-weight:bold; border: 1px solid #d4af37;">View Catalog</a>
    </div>
    '''
    html = build_html_email("Daily Market Intelligence", body)
    send_html_email("Metal Price Update - Triratna Jewels ✦", html, recipient_list)
