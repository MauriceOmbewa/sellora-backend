import uuid

import requests
from django.conf import settings

from .client import get_access_token


def initiate_pochi_payment(
    amount,
    phone,
    remarks="Sellora Payment",
    occasion="Sellora Order",
):
    originator_conversation_id = str(uuid.uuid4())

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "OriginatorConversationID": originator_conversation_id,
        "InitiatorName": settings.MPESA_INITIATOR_NAME,
        "SecurityCredential": settings.MPESA_SECURITY_CREDENTIAL,
        "CommandID": "BusinessPayToPochi",
        "Amount": str(int(amount)),
        "PartyA": settings.MPESA_SHORTCODE,
        "PartyB": phone,
        "Remarks": remarks,
        "QueueTimeOutURL": settings.MPESA_POCHI_TIMEOUT_URL,
        "ResultURL": settings.MPESA_POCHI_RESULT_URL,
        "Occassion": occasion,
    }

    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/b2pochi/v1/paymentrequest",
        json=payload,
        headers=headers,
        timeout=30,
    )

    print("POCHI STATUS:", response.status_code)
    print("POCHI RESPONSE:", response.text)
    print("POCHI PAYLOAD:", payload)

    response.raise_for_status()

    return response.json()