from rest_framework import serializers

from apps.payments.models import PaymentConfiguration


class PaymentConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentConfiguration
        fields = [
            "id",
            "provider",
            "method",
            "paybill_number",
            "paybill_account_reference",
            "till_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        method = attrs.get(
            "method",
            getattr(self.instance, "method", None),
        )

        paybill_number = attrs.get(
            "paybill_number",
            getattr(self.instance, "paybill_number", ""),
        )

        paybill_account_reference = attrs.get(
            "paybill_account_reference",
            getattr(self.instance, "paybill_account_reference", ""),
        )

        till_number = attrs.get(
            "till_number",
            getattr(self.instance, "till_number", ""),
        )

        if method == "paybill":
            if not paybill_number:
                raise serializers.ValidationError(
                    {
                        "paybill_number": (
                            "PayBill number is required when "
                            "PayBill is selected."
                        )
                    }
                )

            if not paybill_account_reference:
                raise serializers.ValidationError(
                    {
                        "paybill_account_reference": (
                            "Account reference is required when "
                            "PayBill is selected."
                        )
                    }
                )

        elif method == "till":
            if not till_number:
                raise serializers.ValidationError(
                    {
                        "till_number": (
                            "Till number is required when "
                            "Till Number is selected."
                        )
                    }
                )

        return attrs