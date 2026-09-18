import base64
from datetime import datetime

import requests
from django.conf import settings

from apps.payments.models import PaymentConfiguration

from .client import get_access_token


def generate_password(shortcode, timestamp):
    """
    Generate the M-Pesa STK Push password.

    Password = Base64(
        BusinessShortCode + Passkey + Timestamp
    )
    """
    data = (
        f"{shortcode}"
        f"{settings.MPESA_PASSKEY}"
        f"{timestamp}"
    )

    return base64.b64encode(data.encode()).decode()


def initiate_stk_push(
    amount,
    phone,
    business,
    account_reference="Sellora Payment",
    transaction_description="Payment for Sellora order",
):
    """
    Initiate an M-Pesa STK Push using the payment configuration
    belonging to the business.

    The merchant's PayBill/Till number is retrieved automatically
    from PaymentConfiguration.

    Args:
        amount: Amount to charge the customer.
        phone: Customer's M-Pesa phone number.
        business: Sellora Business instance.
        account_reference: Reference shown on the M-Pesa transaction.
        transaction_description: Description of the transaction.

    Returns:
        dict: M-Pesa Daraja API response.
    """

    # ------------------------------------------------------------------
    # 1. Get the business payment configuration
    # ------------------------------------------------------------------

    try:
        configuration = PaymentConfiguration.objects.get(
            business=business
        )
    except PaymentConfiguration.DoesNotExist:
        raise ValueError(
            "This business has not configured an M-Pesa payment method."
        )

    # ------------------------------------------------------------------
    # 2. Determine the payment method and merchant number
    # ------------------------------------------------------------------

    payment_method = configuration.method

    if payment_method == PaymentConfiguration.METHOD_PAYBILL:
        merchant_number = configuration.paybill_number

        if not merchant_number:
            raise ValueError(
                "The business has selected PayBill but has not "
                "configured a PayBill number."
            )

        # Use the merchant's configured account reference when
        # one exists and no specific order reference was supplied.
        if (
            account_reference == "Sellora Payment"
            and configuration.paybill_account_reference
        ):
            account_reference = (
                configuration.paybill_account_reference
            )

        transaction_type = "CustomerPayBillOnline"

    elif payment_method == PaymentConfiguration.METHOD_TILL:
        merchant_number = configuration.till_number

        if not merchant_number:
            raise ValueError(
                "The business has selected Till Number but has not "
                "configured a Till Number."
            )

        transaction_type = "CustomerBuyGoodsOnline"

    else:
        raise ValueError(
            "Invalid M-Pesa payment method configured for this business."
        )

    # ------------------------------------------------------------------
    # 3. Generate timestamp
    # ------------------------------------------------------------------

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # ------------------------------------------------------------------
    # 4. Generate STK Push password
    # ------------------------------------------------------------------

    password = generate_password(
        merchant_number,
        timestamp,
    )

    # ------------------------------------------------------------------
    # 5. Get Daraja access token
    # ------------------------------------------------------------------

    access_token = get_access_token()

    # ------------------------------------------------------------------
    # 6. Build request headers
    # ------------------------------------------------------------------

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # ------------------------------------------------------------------
    # 7. Build STK Push payload
    # ------------------------------------------------------------------

    payload = {
        "BusinessShortCode": merchant_number,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": transaction_type,
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": merchant_number,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_description,
    }

    # ------------------------------------------------------------------
    # 8. Send request to Safaricom Daraja
    # ------------------------------------------------------------------

    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers,
        timeout=30,
    )

    # ------------------------------------------------------------------
    # 9. Log response for development/debugging
    # ------------------------------------------------------------------

    print("MPESA STATUS:", response.status_code)
    print("MPESA RESPONSE:", response.text)
    print("BUSINESS:", business.name)
    print("MERCHANT NUMBER:", merchant_number)
    print("PAYMENT METHOD:", payment_method)
    print("TRANSACTION TYPE:", transaction_type)

    # Do not log the customer's phone number or other sensitive
    # payment information unnecessarily.

    # ------------------------------------------------------------------
    # 10. Raise an exception for HTTP errors
    # ------------------------------------------------------------------

    response.raise_for_status()

    # ------------------------------------------------------------------
    # 11. Return Safaricom response
    # ------------------------------------------------------------------

    return response.json()