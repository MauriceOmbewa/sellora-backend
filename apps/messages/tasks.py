"""
Messages Celery tasks.

Currently:
  notify_new_whatsapp_message — email the business owner when a WhatsApp
      message arrives, if email_on_new_message is enabled in their settings.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("apps")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    name="messages.notify_new_whatsapp_message",
)
def notify_new_whatsapp_message(self, conversation_id: str):
    """
    Email the business owner when a new inbound WhatsApp message arrives.

    Checks BusinessSettings.email_on_new_message before sending.
    Triggered by: apps.messages.services.whatsapp._dispatch_whatsapp_message_alert
    """
    try:
        from apps.messages.models import WhatsAppConversation
        from apps.businesses.models import BusinessSettings

        conv = WhatsAppConversation.objects.select_related(
            "business__owner"
        ).get(id=conversation_id)

        biz_settings = BusinessSettings.objects.filter(business=conv.business).first()
        if not biz_settings or not biz_settings.email_on_new_message:
            logger.debug(
                "email_on_new_message disabled for business %s — skipping WhatsApp alert",
                conv.business_id,
            )
            return

        # Grab the last inbound message for preview
        last_msg = conv.messages.filter(direction="inbound").order_by("-created_at").first()
        preview = last_msg.body[:120] if last_msg else "(media message)"

        owner_email = conv.business.owner.email
        subject = f"New WhatsApp message from {conv.customer_name} — {conv.business.name}"
        body = (
            f"Hi {conv.business.owner.name},\n\n"
            f"You have a new WhatsApp message.\n\n"
            f"From: {conv.customer_name} ({conv.customer_phone})\n\n"
            f'Message:\n"{preview}"\n\n'
            f"Reply at: {settings.FRONTEND_URL}/app/messages\n\n"
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
            "WhatsApp message alert sent to %s for conversation %s",
            owner_email, conversation_id,
        )

    except Exception as exc:
        logger.error(
            "notify_new_whatsapp_message failed for conversation %s: %s",
            conversation_id, exc,
        )
        raise self.retry(exc=exc)
