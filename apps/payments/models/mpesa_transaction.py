"""
MpesaTransaction — records every STK Push request and its outcome.

A transaction is created BEFORE the order. The M-Pesa callback
sets the result. If the payment succeeds, the order is created then.
If it fails or times out, the transaction is marked failed/expired
and no order is ever created.
"""
import uuid
from django.db import models

from apps.businesses.models import Business


class MpesaTransaction(models.Model):
    """
    Tracks a single STK Push request and its Safaricom callback result.

    Lifecycle:
        pending  → customer has been prompted, awaiting PIN entry
        paid     → callback received, ResultCode == 0 (success)
        failed   → callback received, ResultCode != 0 (declined/error)
        expired  → no callback received within timeout window
    """

    STATUS_PENDING = "pending"
    STATUS_PAID    = "paid"
    STATUS_FAILED  = "failed"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID,    "Paid"),
        (STATUS_FAILED,  "Failed"),
        (STATUS_EXPIRED, "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ── Identifiers ──────────────────────────────────────────────────────────
    # MerchantRequestID returned by Daraja (useful for support)
    merchant_request_id = models.CharField(max_length=100, blank=True, default="")

    # CheckoutRequestID returned by Daraja — used as the polling key
    checkout_request_id = models.CharField(
        max_length=100, unique=True, db_index=True
    )

    # ── Business / payment config ─────────────────────────────────────────────
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="mpesa_transactions",
    )

    # ── Customer details (captured at STK push time) ──────────────────────────
    phone = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # ── Cart snapshot — everything needed to create the order later ───────────
    # Stored as JSON: { customer_name, customer_phone, customer_email,
    #   delivery_address, order_notes, payment_method, channel,
    #   fulfillment_type, items: [{product_id, quantity}],
    #   discount, custom_delivery_fee }
    cart_snapshot = models.JSONField(default=dict)

    # ── Status ────────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    # ── Callback payload (raw, for debugging) ────────────────────────────────
    callback_payload = models.JSONField(null=True, blank=True)

    # ── Result from callback ──────────────────────────────────────────────────
    result_code = models.CharField(max_length=10, blank=True, default="")
    result_desc = models.CharField(max_length=255, blank=True, default="")
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, default="")

    # ── Linked order (set after successful payment + order creation) ──────────
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mpesa_transaction",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "M-Pesa Transaction"
        verbose_name_plural = "M-Pesa Transactions"

    def __str__(self):
        return (
            f"MpesaTransaction {self.checkout_request_id} "
            f"[{self.status}] KSh {self.amount}"
        )
