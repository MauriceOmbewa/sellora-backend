import base64
import requests

from django.conf import settings


def get_access_token():
    credentials = (
        f"{settings.MPESA_CONSUMER_KEY}:"
        f"{settings.MPESA_CONSUMER_SECRET}"
    )

    encoded_credentials = base64.b64encode(
        credentials.encode()
    ).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}"
    }

    response = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate"
        "?grant_type=client_credentials",
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["access_token"]