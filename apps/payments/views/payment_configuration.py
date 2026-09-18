from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.models import Business
from apps.payments.models import PaymentConfiguration
from apps.payments.serializers import PaymentConfigurationSerializer


class PaymentConfigurationView(APIView):
    """
    Retrieve or update the payment configuration for a business.
    """

    permission_classes = [IsAuthenticated]

    def get_business(self, request, business_id):
        try:
            return Business.objects.get(
                id=business_id,
                owner=request.user,
            )
        except Business.DoesNotExist:
            return None

    def get(self, request, business_id):
        business = self.get_business(request, business_id)

        if not business:
            return Response(
                {"detail": "Business not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            configuration = PaymentConfiguration.objects.get(
                business=business
            )
        except PaymentConfiguration.DoesNotExist:
            return Response(
                {"detail": "Payment configuration not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PaymentConfigurationSerializer(configuration)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request, business_id):
        business = self.get_business(request, business_id)

        if not business:
            return Response(
                {"detail": "Business not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if PaymentConfiguration.objects.filter(
            business=business
        ).exists():
            return Response(
                {
                    "detail": (
                        "Payment configuration already exists. "
                        "Use PATCH to update it."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PaymentConfigurationSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        configuration = serializer.save(
            business=business
        )

        return Response(
            PaymentConfigurationSerializer(configuration).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, business_id):
        business = self.get_business(request, business_id)

        if not business:
            return Response(
                {"detail": "Business not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            configuration = PaymentConfiguration.objects.get(
                business=business
            )
        except PaymentConfiguration.DoesNotExist:
            return Response(
                {"detail": "Payment configuration not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PaymentConfigurationSerializer(
            configuration,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )