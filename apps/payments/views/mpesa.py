"""
M-Pesa payment views.

Flow:
  1. STKInitiateView   POST /api/v1/payments/mpesa/initiate/
       • Receives full cart + customer details
       • Calculates order total (validates stock, applies delivery fee)
       • Creates a pending MpesaTransaction (cart snapshot stored here)
       • Initiates STK Push via Daraja
       • Returns checkout_request_id for the frontend to poll

  2. MpesaCallbackView POST /api/v1/payments/mpesa/callback/
       • Receives Safaricom's async callback
       • On ResultCode == 0 (success):
           - Creates the real Order from the cart snapshot
           - Marks the order as paid
           - Marks the MpesaTransaction as paid + stores receipt
       • On failure:
           - Marks MpesaTransaction as failed, stores description

  3. MpesaStatusView   GET /api/v1/payments/mpesa/status/<checkout_request_id>/
       • Frontend polls this every 3 s
       • Returns { status, order_number, order_id }
       • Frontend navigates to /success when status == "paid"
         or shows an error message when status == "failed"
"""
import logging
from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.businesses.models import Business  # kept for type hints in legacy STKPushView
from apps.orders.models import Order
from apps.payments.models import MpesaTransaction
from apps.payments.serializers.mpesa import (
    STKInitiateSerializer,
    STKPushSerializer,
    PochiPaymentSerializer,
)
from apps.payments.services.mpesa.stk_push import initiate_stk_push
from apps.payments.services.mpesa.pochi import initiate_pochi_payment

logger = logging.getLogger("apps")


# ---------------------------------------------------------------------------
# Helper: compute order total without creating the order
# ---------------------------------------------------------------------------

def _calculate_total(business, items: list, fulfillment_type: str,
                     discount: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """
    Validate stock and calculate (subtotal, delivery_fee, total).
    Raises ValueError on stock or product issues.
    Returns (subtotal, delivery_fee, total).
    """
    from apps.products.models import Product
    from apps.orders.constants import DELIVERY_FEE, FREE_DELIVERY_THRESHOLD

    subtotal = Decimal("0")

    for item_data in items:
        product_id = item_data.get("product_id")
        quantity = int(item_data.get("quantity", 1))

        try:
            product = Product.objects.get(
                id=product_id,
                business=business,
                status="active",
            )
        except Product.DoesNotExist:
            raise ValueError(
                f"Product {product_id} is not available in this store."
            )

        if product.stock_quantity < quantity:
            raise ValueError(
                f"Insufficient stock for '{product.name}': "
                f"requested {quantity}, available {product.stock_quantity}."
            )

        unit_price = product.sale_price or product.selling_price
        subtotal += unit_price * quantity

    # Delivery fee
    if fulfillment_type == "pickup":
        delivery_fee = Decimal("0")
    else:
        try:
            s = business.settings
            biz_fee = Decimal(str(s.delivery_fee))
            biz_threshold = Decimal(str(s.free_delivery_threshold))
        except Exception:
            biz_fee = Decimal(str(DELIVERY_FEE))
            biz_threshold = Decimal(str(FREE_DELIVERY_THRESHOLD))

        delivery_fee = Decimal("0") if subtotal >= biz_threshold else biz_fee

    total = subtotal + delivery_fee - discount
    return subtotal, delivery_fee, total


# ---------------------------------------------------------------------------
# 1. STK Initiate — replaces the old STKPushView for storefront checkout
# ---------------------------------------------------------------------------

class STKInitiateView(APIView):
    """
    POST /api/v1/payments/mpesa/initiate/

    Receives full cart details, calculates the amount, creates a
    pending MpesaTransaction, and sends the STK Push to the customer.

    No order is created yet — that happens in the callback.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = STKInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # ── 1. Resolve the business (reuse the same selector as storefront views)
        from apps.businesses.selectors import get_business_by_slug
        business = get_business_by_slug(data["business_slug"])
        if not business:
            return Response(
                {"detail": "Store not found or unavailable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Ensure settings are cached for delivery fee calculation
        try:
            _ = business.settings
        except Exception:
            pass

        # ── 2. Validate stock + calculate total ───────────────────────
        try:
            subtotal, delivery_fee, total = _calculate_total(
                business,
                data["items"],
                data["fulfillment_type"],
                data["discount"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if total <= 0:
            return Response(
                {"detail": "Order total must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = data["customer_phone"]

        # ── 3. Build cart snapshot (everything needed to create the order later)
        cart_snapshot = {
            "customer_name":     data["customer_name"],
            "customer_phone":    phone,
            "customer_email":    data.get("customer_email", ""),
            "delivery_address":  data.get("delivery_address", ""),
            "order_notes":       data.get("order_notes", ""),
            "fulfillment_type":  data["fulfillment_type"],
            "payment_method":    "mpesa",
            "channel":           "online",
            "items":             data["items"],
            "discount":          str(data["discount"]),
            "subtotal":          str(subtotal),
            "delivery_fee":      str(delivery_fee),
        }

        # ── 4. Initiate STK Push ──────────────────────────────────────
        try:
            daraja_response = initiate_stk_push(
                amount=total,
                phone=phone,
                business=business,
                account_reference=f"Order from {business.name}",
                transaction_description=f"Payment to {business.name}",
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error("STK push failed for business %s: %s", business.id, exc)
            return Response(
                {"detail": "Failed to send M-Pesa request. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        checkout_request_id = daraja_response.get("CheckoutRequestID", "")
        merchant_request_id = daraja_response.get("MerchantRequestID", "")

        if not checkout_request_id:
            logger.error(
                "Daraja response missing CheckoutRequestID: %s", daraja_response
            )
            return Response(
                {"detail": "Invalid response from M-Pesa. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ── 5. Persist pending transaction ────────────────────────────
        # Use update_or_create in case Safaricom reuses a CheckoutRequestID
        # (can happen when retrying quickly after a cancellation).
        MpesaTransaction.objects.update_or_create(
            checkout_request_id=checkout_request_id,
            defaults=dict(
                merchant_request_id=merchant_request_id,
                business=business,
                phone=phone,
                amount=total,
                cart_snapshot=cart_snapshot,
                status=MpesaTransaction.STATUS_PENDING,
                # Reset any previous failure state
                result_code="",
                result_desc="",
                mpesa_receipt_number="",
                callback_payload=None,
                order=None,
            ),
        )

        logger.info(
            "STK push initiated for business %s — CheckoutRequestID %s — KSh %s",
            business.id, checkout_request_id, total,
        )

        return Response(
            {
                "message": (
                    "M-Pesa payment request sent. "
                    "Please check your phone and enter your M-Pesa PIN."
                ),
                "checkout_request_id": checkout_request_id,
                "amount": str(total),
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# 2. Callback — Safaricom POSTs here after the customer acts on the prompt
# ---------------------------------------------------------------------------

class MpesaCallbackView(APIView):
    """
    POST /api/v1/payments/mpesa/callback/

    Safaricom sends the final payment result here.
    This endpoint MUST be publicly accessible (no auth).

    On success  → create the order, mark transaction paid
    On failure  → mark transaction failed
    """

    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data

        logger.info("M-Pesa callback received: %s", payload)

        try:
            body = payload.get("Body", {})
            stk_callback = body.get("stkCallback", {})

            merchant_request_id  = stk_callback.get("MerchantRequestID", "")
            checkout_request_id  = stk_callback.get("CheckoutRequestID", "")
            result_code          = str(stk_callback.get("ResultCode", ""))
            result_desc          = stk_callback.get("ResultDesc", "")

            # Find the pending transaction
            try:
                txn = MpesaTransaction.objects.select_related(
                    "business"
                ).get(checkout_request_id=checkout_request_id)
            except MpesaTransaction.DoesNotExist:
                logger.warning(
                    "Callback for unknown CheckoutRequestID: %s",
                    checkout_request_id,
                )
                return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

            # Prevent duplicate processing
            if txn.status != MpesaTransaction.STATUS_PENDING:
                logger.info(
                    "Callback for already-processed transaction %s (status=%s)",
                    checkout_request_id, txn.status,
                )
                return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

            # Always store the raw payload
            txn.callback_payload = payload
            txn.result_code = result_code
            txn.result_desc = result_desc

            if result_code == "0":
                # ── Payment succeeded ─────────────────────────────────
                # Extract M-Pesa receipt number from callback metadata
                mpesa_receipt = ""
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                for item in callback_metadata.get("Item", []):
                    if item.get("Name") == "MpesaReceiptNumber":
                        mpesa_receipt = str(item.get("Value", ""))
                        break

                txn.mpesa_receipt_number = mpesa_receipt

                # Create the order from the stored cart snapshot
                try:
                    order = _create_order_from_snapshot(txn)
                    txn.status = MpesaTransaction.STATUS_PAID
                    txn.order = order
                    txn.save(update_fields=[
                        "status", "result_code", "result_desc",
                        "mpesa_receipt_number", "callback_payload",
                        "order", "updated_at",
                    ])
                    logger.info(
                        "Order %s created from M-Pesa transaction %s (receipt: %s)",
                        order.order_number, checkout_request_id, mpesa_receipt,
                    )
                except Exception as exc:
                    # Order creation failed — mark as paid but log the error
                    # so it can be manually recovered. Do NOT return error to
                    # Safaricom (they would keep retrying).
                    logger.error(
                        "Failed to create order for M-Pesa transaction %s: %s",
                        checkout_request_id, exc,
                    )
                    txn.status = MpesaTransaction.STATUS_PAID
                    txn.save(update_fields=[
                        "status", "result_code", "result_desc",
                        "mpesa_receipt_number", "callback_payload", "updated_at",
                    ])

            else:
                # ── Payment failed / cancelled ────────────────────────
                txn.status = MpesaTransaction.STATUS_FAILED
                txn.save(update_fields=[
                    "status", "result_code", "result_desc",
                    "callback_payload", "updated_at",
                ])
                logger.info(
                    "M-Pesa payment failed for transaction %s: %s (code=%s)",
                    checkout_request_id, result_desc, result_code,
                )

        except Exception as exc:
            # Never return a non-200 to Safaricom — they will retry
            logger.error("Error processing M-Pesa callback: %s", exc)

        # Safaricom expects exactly this response
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


def _create_order_from_snapshot(txn: MpesaTransaction) -> Order:
    """
    Create an Order from the cart snapshot stored on the MpesaTransaction.
    Marks the order as paid immediately.
    """
    from apps.orders.services import create_order

    snap = txn.cart_snapshot
    discount = Decimal(snap.get("discount", "0"))

    # custom_delivery_fee: use snapshot value so the amount matches
    # exactly what the customer was charged
    custom_delivery_fee = Decimal(snap.get("delivery_fee", "0"))

    with transaction.atomic():
        order = create_order(
            txn.business,
            customer_name=snap["customer_name"],
            customer_phone=snap["customer_phone"],
            customer_email=snap.get("customer_email", ""),
            delivery_address=snap.get("delivery_address", ""),
            order_notes=snap.get("order_notes", ""),
            payment_method="mpesa",
            channel=snap.get("channel", "online"),
            items=snap["items"],
            discount=discount,
            custom_delivery_fee=custom_delivery_fee,
            fulfillment_type=snap.get("fulfillment_type", "delivery"),
        )

        # Mark the order as paid immediately
        order.payment_status = "paid"
        order.save(update_fields=["payment_status", "updated_at"])

    return order


# ---------------------------------------------------------------------------
# Helper: query Safaricom and update the transaction in-place
# ---------------------------------------------------------------------------

def _query_and_resolve(txn: MpesaTransaction) -> dict | None:
    """
    Call Safaricom's STK Query API for a pending transaction.

    If Safaricom returns a definitive result (success or failure),
    update the MpesaTransaction and, on success, create the order.

    Returns:
        dict  — resolved status payload to return to the frontend
        None  — transaction is still genuinely pending (no result yet)
    """
    from apps.payments.services.mpesa.stk_query import query_stk_status

    try:
        result = query_stk_status(txn.checkout_request_id)
    except Exception:
        raise

    # Safaricom uses two different "still pending" response shapes:
    #
    # Shape A — errorCode body (customer hasn't acted yet):
    #   {"errorCode": "500.001.1001", "errorMessage": "The transaction is being processed"}
    #
    # Shape B — ResultCode body that means "not settled yet":
    #   {"ResultCode": "4999", "ResultDesc": "The transaction is still under processing"}
    #   {"ResultCode": "1037", "ResultDesc": "DS timeout user cannot be reached"}
    #
    # These must all be treated as PENDING, not failures.

    STILL_PENDING_ERROR_CODES = {"500.001.1001"}
    # ResultCodes that are transient / not yet final
    STILL_PENDING_RESULT_CODES = {"4999", "1037"}

    if "errorCode" in result:
        error_code = result.get("errorCode", "")
        if any(c in error_code for c in STILL_PENDING_ERROR_CODES):
            return None
        logger.warning("STK query unhandled errorCode response: %s", result)
        return None

    result_code = str(result.get("ResultCode", ""))
    result_desc = result.get("ResultDesc", "")

    # Transient codes — keep polling
    if result_code in STILL_PENDING_RESULT_CODES:
        logger.debug(
            "STK query %s returned transient code %s ('%s') — keeping pending",
            txn.checkout_request_id, result_code, result_desc,
        )
        return None

    if result_code == "0":
        # ── Payment confirmed ─────────────────────────────────────────
        # Guard: don't create a duplicate order if somehow already paid
        txn.refresh_from_db(fields=["status", "order_id"])
        if txn.status == MpesaTransaction.STATUS_PAID and txn.order_id:
            return {
                "status":       "paid",
                "order_id":     str(txn.order_id),
                "order_number": txn.order.order_number if txn.order else "",
            }
        try:
            order = _create_order_from_snapshot(txn)
            txn.status = MpesaTransaction.STATUS_PAID
            txn.order = order
            txn.result_code = result_code
            txn.result_desc = result_desc
            txn.save(update_fields=[
                "status", "result_code", "result_desc", "order", "updated_at",
            ])
            logger.info(
                "Order %s created via STK query for transaction %s",
                order.order_number, txn.checkout_request_id,
            )
            return {
                "status":       "paid",
                "order_id":     str(order.id),
                "order_number": order.order_number,
            }
        except Exception as exc:
            logger.error(
                "Order creation failed after STK query success (%s): %s",
                txn.checkout_request_id, exc,
            )
            txn.status = MpesaTransaction.STATUS_PAID
            txn.result_code = result_code
            txn.result_desc = result_desc
            txn.save(update_fields=["status", "result_code", "result_desc", "updated_at"])
            return {"status": "paid"}

    # ── Definitively terminal non-zero result codes ───────────────────
    # 1032 = Request cancelled by user
    # 1    = Insufficient funds
    # 2001 = Wrong PIN / max retries exceeded
    # Any other non-empty, non-transient code = definitive failure
    if result_code:
        txn.status = MpesaTransaction.STATUS_FAILED
        txn.result_code = result_code
        txn.result_desc = result_desc
        txn.save(update_fields=[
            "status", "result_code", "result_desc", "updated_at",
        ])
        logger.info(
            "STK transaction %s failed via query: %s (code=%s)",
            txn.checkout_request_id, result_desc, result_code,
        )
        return {
            "status": "failed",
            "reason": result_desc or "Payment was not completed.",
        }

    return None


# ---------------------------------------------------------------------------
# 3. Status polling — frontend calls this every 3 s after STK push
# ---------------------------------------------------------------------------

class MpesaStatusView(APIView):
    """
    GET /api/v1/payments/mpesa/status/<checkout_request_id>/

    Returns the current state of an STK Push transaction.

    On every call where the transaction is still pending, this view
    actively queries Safaricom's STK Query API so the result is
    discovered even when the callback URL is unreachable (e.g. localhost).

    Possible responses:
      { "status": "pending" }              — still waiting for customer PIN
      { "status": "paid",
        "order_id": "...",
        "order_number": "#1001" }          — payment confirmed, order created
      { "status": "failed",
        "reason": "Request cancelled..." } — customer declined or error
      { "status": "expired" }              — no callback within timeout
    """

    permission_classes = [AllowAny]

    def get(self, request, checkout_request_id):
        try:
            txn = MpesaTransaction.objects.select_related("order").get(
                checkout_request_id=checkout_request_id
            )
        except MpesaTransaction.DoesNotExist:
            return Response(
                {"detail": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Already resolved by callback — return immediately ─────────
        if txn.status == MpesaTransaction.STATUS_PAID:
            response_data = {"status": "paid"}
            if txn.order:
                response_data["order_id"]     = str(txn.order.id)
                response_data["order_number"] = txn.order.order_number
            return Response(response_data)

        if txn.status == MpesaTransaction.STATUS_FAILED:
            return Response({
                "status": "failed",
                "reason": txn.result_desc or "Payment was not completed.",
            })

        if txn.status == MpesaTransaction.STATUS_EXPIRED:
            return Response({"status": "expired"})

        # ── Still pending — actively query Safaricom ──────────────────
        # This makes polling work even when the callback URL is not
        # publicly reachable (localhost / ngrok not set up, etc.).
        try:
            query_result = _query_and_resolve(txn)
            if query_result:
                return Response(query_result)
        except Exception as exc:
            # Query API failure is non-fatal — keep polling
            logger.warning(
                "STK query failed for %s: %s", checkout_request_id, exc
            )

        return Response({"status": "pending"})


# ---------------------------------------------------------------------------
# Legacy STKPushView — kept so existing dashboard routes don't break
# ---------------------------------------------------------------------------

class STKPushView(APIView):
    """
    DEPRECATED: use STKInitiateView for storefront checkout.

    Still used internally — initiates an STK push against an existing
    order (e.g. for retry from dashboard).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = STKPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order_id = data["order_id"]
        phone    = data["phone"]

        try:
            order = Order.objects.select_related("business").get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.payment_status == "paid":
            return Response(
                {"detail": "This order has already been paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.customer_phone = phone
        order.payment_method = "mpesa"
        order.payment_status = "pending"
        order.save(update_fields=[
            "customer_phone", "payment_method", "payment_status", "updated_at",
        ])

        try:
            result = initiate_stk_push(
                amount=order.total,
                phone=phone,
                business=order.business,
                account_reference=order.order_number,
                transaction_description=f"Payment for order {order.order_number}",
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": (
                "M-Pesa payment request sent. "
                "Please check your phone and enter your M-Pesa PIN."
            ),
            "order_id":       str(order.id),
            "order_number":   order.order_number,
            "amount":         str(order.total),
            "payment_method": order.payment_method,
            "mpesa_response": result,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Pochi view (unchanged)
# ---------------------------------------------------------------------------

class PochiPaymentView(APIView):

    def post(self, request):
        serializer = PochiPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = initiate_pochi_payment(
            amount=data["amount"],
            phone=data["phone"],
            remarks=data.get("remarks", "Sellora Payment"),
            occasion=data.get("occasion", "Sellora Order"),
        )

        return Response(result, status=status.HTTP_200_OK)
