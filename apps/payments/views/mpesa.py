from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.orders.models import Order
from apps.payments.serializers.mpesa import (
    STKPushSerializer,
    PochiPaymentSerializer,
)
from apps.payments.services.mpesa.stk_push import initiate_stk_push
from apps.payments.services.mpesa.pochi import initiate_pochi_payment


class STKPushView(APIView):
    """
    Initiate an M-Pesa STK Push for an existing Sellora order.

    The frontend only provides:
        - order_id
        - customer's phone number

    The backend gets:
        - business
        - order amount
        - order number
        - payment configuration
        - PayBill/Till number

    from the database.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = STKPushSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        order_id = data["order_id"]
        phone = data["phone"]

        # --------------------------------------------------------------
        # 1. Get the order
        # --------------------------------------------------------------

        try:
            order = Order.objects.select_related(
                "business"
            ).get(id=order_id)

        except Order.DoesNotExist:
            return Response(
                {
                    "detail": "Order not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # --------------------------------------------------------------
        # 2. Make sure the order can be paid
        # --------------------------------------------------------------

        if order.payment_status == "paid":
            return Response(
                {
                    "detail": "This order has already been paid."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------------------
        # 3. Save the customer's phone number to the order
        # --------------------------------------------------------------

        order.customer_phone = phone
        order.payment_method = "mpesa"
        order.payment_status = "pending"
        order.save(
            update_fields=[
                "customer_phone",
                "payment_method",
                "payment_status",
                "updated_at",
            ]
        )

        # --------------------------------------------------------------
        # 4. Initiate STK Push
        # --------------------------------------------------------------

        try:
            result = initiate_stk_push(
                amount=order.total,
                phone=phone,
                business=order.business,
                account_reference=order.order_number,
                transaction_description=(
                    f"Payment for order {order.order_number}"
                ),
            )

        except ValueError as e:
            return Response(
                {
                    "detail": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            return Response(
                {
                    "detail": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # --------------------------------------------------------------
        # 5. Return STK Push response to frontend
        # --------------------------------------------------------------

        return Response(
            {
                "message": (
                    "M-Pesa payment request sent. "
                    "Please check your phone and enter your M-Pesa PIN."
                ),
                "order_id": str(order.id),
                "order_number": order.order_number,
                "amount": str(order.total),
                "payment_method": order.payment_method,
                "mpesa_response": result,
            },
            status=status.HTTP_200_OK,
        )


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

        return Response(
            result,
            status=status.HTTP_200_OK,
        )