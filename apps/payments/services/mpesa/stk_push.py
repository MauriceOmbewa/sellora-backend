import base64
from datetime import datetime

import requests
from django.conf import settings

from .client import get_access_token


def generate_password(timestamp):
    data = (
        f"{settings.MPESA_SHORTCODE}"
        f"{settings.MPESA_PASSKEY}"
        f"{timestamp}"
    )

    return base64.b64encode(data.encode()).decode()


def initiate_stk_push(
    amount,
    phone,
    account_reference="Sellora Payment",
    transaction_description="Payment for Sellora order",
):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password = generate_password(timestamp)

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_description,
    }

    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()