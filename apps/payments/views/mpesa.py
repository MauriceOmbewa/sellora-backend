from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.payments.serializers.mpesa import STKPushSerializer
from apps.payments.services.mpesa.stk_push import initiate_stk_push


class STKPushView(APIView):

    def post(self, request):
        serializer = STKPushSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            result = initiate_stk_push(
                amount=int(data["amount"]),
                phone=data["phone"],
                account_reference=data["account_reference"],
                transaction_description=data["transaction_description"],
            )

            return Response(
                result,
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )