"""
Notification Celery tasks.

Each task checks the BusinessSettings notification preferences before
sending — if the owner has disabled a notification type, nothing is sent.

Tasks are designed to be idempotent and retried on transient failures
(e.g. SMTP timeouts). They use bind=True + autoretry_for for safety.

All tasks accept primitive arguments (IDs, not model instances) so
they serialize cleanly through the Celery message broker.
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger("apps")


# ─── New Order ────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    name="notifications.send_new_order_email",
)
def send_new_order_email(self, order_id: str):
    """
    Email the business owner when a new order arrives.
    Triggered by: orders.services.create_order (after commit).

    Checks: business_settings.email_on_new_order
    """
    try:
        from apps.orders.models import Order
        from apps.businesses.models import BusinessSettings

        order = Order.objects.select_related(
            "business__owner", "business"
        ).prefetch_related("items").get(id=order_id)

        biz_settings = BusinessSettings.objects.filter(
            business=order.business
        ).first()

        if not biz_settings or not biz_settings.email_on_new_order:
            logger.debug(
                "email_on_new_order disabled for business %s — skipping",
                order.business_id,
            )
            return

        owner_email = order.business.owner.email
        subject = f"New order {order.order_number} — {order.business.name}"

        message = (
            f"Hi {order.business.owner.name},\n\n"
            f"You have a new order!\n\n"
            f"Order: {order.order_number}\n"
            f"Customer: {order.customer_name} ({order.customer_phone})\n"
            f"Total: KSh {order.total:,.0f}\n"
            f"Payment: {order.get_payment_method_display()}\n"
            f"Channel: {order.get_channel_display()}\n\n"
            f"Items:\n"
        )
        for item in order.items.all():
            message += f"  • {item.quantity}× {item.product_name} — KSh {item.total_price:,.0f}\n"

        message += f"\nView order at: {settings.FRONTEND_URL}/dashboard/orders/{order.id}"

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner_email],
            fail_silently=False,
        )

        logger.info(
            "New order email sent to %s for order %s",
            owner_email, order.order_number,
        )

    except Exception as exc:
        logger.error("send_new_order_email failed for order %s: %s", order_id, exc)
        raise self.retry(exc=exc)


# ─── Order Status Changed ─────────────────────────────────────────────────────

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    name="notifications.send_order_status_email",
)
def send_order_status_email(self, order_id: str, new_status: str):
    """
    Notify the customer when their order status changes.
    Only sent if the order has a customer_email.
    """
    try:
        from apps.orders.models import Order

        order = Order.objects.select_related("business").get(id=order_id)

        if not order.customer_email:
            return  # No customer email — nothing to send

        status_messages = {
            "confirmed": "Your order has been confirmed and is being prepared.",
            "processing": "Your order is currently being processed.",
            "ready": "Your order is ready! We'll be in touch shortly.",
            "completed": "Your order has been delivered. Thank you for shopping with us!",
            "cancelled": "Your order has been cancelled. Contact us if you have questions.",
        }

        message_body = status_messages.get(new_status)
        if not message_body:
            return

        subject = f"Order {order.order_number} update — {order.business.name}"
        message = (
            f"Hi {order.customer_name},\n\n"
            f"{message_body}\n\n"
            f"Order: {order.order_number}\n"
            f"Status: {new_status.title()}\n\n"
            f"Thank you,\n{order.business.name}"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            fail_silently=False,
        )

        logger.info(
            "Order status email sent to %s for order %s → %s",
            order.customer_email, order.order_number, new_status,
        )

    except Exception as exc:
        logger.error("send_order_status_email failed for order %s: %s", order_id, exc)
        raise self.retry(exc=exc)


# ─── Low Stock Alert ──────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 120},
    name="notifications.send_low_stock_alert",
)
def send_low_stock_alert(self, product_id: str):
    """
    Email the business owner when a product falls to or below
    its low_stock_threshold.

    Checks: business_settings.email_on_low_stock
    Triggered by: products stock adjustment or order placement.
    """
    try:
        from apps.products.models import Product
        from apps.businesses.models import BusinessSettings

        product = Product.objects.select_related(
            "business__owner"
        ).get(id=product_id)

        biz_settings = BusinessSettings.objects.filter(
            business=product.business
        ).first()

        if not biz_settings or not biz_settings.email_on_low_stock:
            return

        owner_email = product.business.owner.email
        subject = f"Low stock alert: {product.name} — {product.business.name}"
        message = (
            f"Hi {product.business.owner.name},\n\n"
            f"'{product.name}' is running low on stock.\n\n"
            f"Current stock: {product.stock_quantity} units\n"
            f"Low stock threshold: {product.low_stock_threshold} units\n"
            f"SKU: {product.sku or 'N/A'}\n\n"
            f"Restock at: {settings.FRONTEND_URL}/dashboard/inventory\n\n"
            f"— Sellora"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner_email],
            fail_silently=False,
        )

        logger.info(
            "Low stock alert sent to %s for product %s (qty=%d)",
            owner_email, product.name, product.stock_quantity,
        )

    except Exception as exc:
        logger.error("send_low_stock_alert failed for product %s: %s", product_id, exc)
        raise self.retry(exc=exc)


# ─── New Customer Message ─────────────────────────────────────────────────────

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    name="notifications.send_new_message_alert",
)
def send_new_message_alert(self, message_id: str):
    """
    Email the business owner when a customer submits a contact form message.

    Checks: business_settings.email_on_new_message
    Triggered by: messages.services.create_message
    """
    try:
        from apps.messages.models import CustomerMessage
        from apps.businesses.models import BusinessSettings

        msg = CustomerMessage.objects.select_related(
            "business__owner"
        ).get(id=message_id)

        biz_settings = BusinessSettings.objects.filter(
            business=msg.business
        ).first()

        if not biz_settings or not biz_settings.email_on_new_message:
            return

        owner_email = msg.business.owner.email
        subject = f"New message from {msg.sender_name} — {msg.business.name}"
        body = (
            f"Hi {msg.business.owner.name},\n\n"
            f"You have a new message from your storefront.\n\n"
            f"From: {msg.sender_name}\n"
            f"Phone: {msg.sender_phone or 'Not provided'}\n"
            f"Email: {msg.sender_email or 'Not provided'}\n"
            f"Channel: {msg.channel}\n\n"
            f"Message:\n{msg.body}\n\n"
            f"Reply at: {settings.FRONTEND_URL}/dashboard/messages\n\n"
            f"— Sellora"
        )

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner_email],
            fail_silently=False,
        )

        logger.info(
            "New message alert sent to %s for message %s",
            owner_email, message_id,
        )

    except Exception as exc:
        logger.error("send_new_message_alert failed for message %s: %s", message_id, exc)
        raise self.retry(exc=exc)
