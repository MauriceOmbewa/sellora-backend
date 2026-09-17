from django.db import models

from apps.businesses.models import Business
from apps.core.models import BaseModel


class PaymentConfiguration(BaseModel):
    """
    Stores the payment configuration for a business.

    A business can currently configure one payment method.
    More payment providers/methods can be added later.
    """

    PROVIDER_M_PESA = "mpesa"

    PROVIDER_CHOICES = [
        (PROVIDER_M_PESA, "M-Pesa"),
    ]

    METHOD_PAYBILL = "paybill"
    METHOD_TILL = "till"

    METHOD_CHOICES = [
        (METHOD_PAYBILL, "PayBill"),
        (METHOD_TILL, "Till Number"),
    ]

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="payment_configuration",
    )

    provider = models.CharField(
        max_length=30,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_M_PESA,
    )

    method = models.CharField(
        max_length=30,
        choices=METHOD_CHOICES,
    )

    paybill_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    paybill_account_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    till_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    def __str__(self):
        return f"{self.business.name} - {self.provider} - {self.method}"