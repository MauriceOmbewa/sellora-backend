"""
POST /api/v1/businesses/{business_id}/whatsapp/connect/

Called by the frontend immediately after the Meta Embedded Signup popup
closes successfully.  The popup returns three values via the JS SDK:
  - code           (short-lived authorisation code)
  - waba_id        (WhatsApp Business Account ID)
  - phone_number_id

This view exchanges the code for a permanent token, subscribes webhooks,
and saves everything.  The business never touches API keys.
"""
import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import serializers

from apps.businesses.permissions import IsBusinessOwner
from apps.messages.services.embedded_signup import complete_embedded_signup
from common.exceptions import ValidationError
from common.responses import created_response

logger = logging.getLogger("apps")


class EmbeddedSignupSerializer(serializers.Serializer):
    """Payload sent by the frontend after popup completion."""
    code            = serializers.CharField(max_length=512)
    waba_id         = serializers.CharField(max_length=50)
    phone_number_id = serializers.CharField(max_length=50)


class WhatsAppEmbeddedSignupView(APIView):
    """
    POST /businesses/{business_id}/whatsapp/connect/

    Completes the Embedded Signup server-side flow:
      1. Exchange code → business token
      2. Resolve phone number
      3. Subscribe webhooks on WABA
      4. Register number for Cloud API
      5. Save WhatsAppSettings
    """
    permission_classes = [IsAuthenticated, IsBusinessOwner]

    def post(self, request, business_id):
        ser = EmbeddedSignupSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        try:
            result = complete_embedded_signup(
                request.business,
                code=d["code"],
                waba_id=d["waba_id"],
                phone_number_id=d["phone_number_id"],
            )
        except ValueError as exc:
            raise ValidationError(str(exc))

        return created_response(
            data=result,
            message=f"WhatsApp connected successfully.",
        )
