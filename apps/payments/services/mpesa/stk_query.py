"""
M-Pesa STK Push Query — Daraja API.

Used to actively check whether a customer completed or cancelled
an STK Push prompt.  This is the fallback when the callback URL
is not reachable (e.g. localhost development) and also makes the
polling more reliable in production.

Safaricom endpoint:
  POST https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query

Result codes of interest:
  0          — transaction successful
  1032       — request cancelled by user
  1037       — timeout (DS timeout)
  17         — transaction failed (insufficient funds, etc.)
  2001       — wrong PIN
  1001       — insufficient funds

Non-zero ResultCode means the payment did not go through.

Reference:
  https://developer.safaricom.co.ke/Documentation
"""
import base64
import logging
from datetime import datetime

import requests
from django.conf import settings

from .client import get_access_token

logger = logging.getLogger("apps")


def query_stk_status(
    checkout_request_id: str,
    shortcode: str = None,
    passkey: str = None,
) -> dict:
    """
    Query Safaricom for the current status of an STK Push request.

    Args:
        checkout_request_id: The CheckoutRequestID returned by the STK push.
        shortcode: Business shortcode. Defaults to settings.MPESA_SHORTCODE.
        passkey: Lipa na M-Pesa passkey. Defaults to settings.MPESA_PASSKEY.

    Returns:
        dict: Safaricom JSON response containing ResultCode and ResultDesc.
              Example success:  {"ResultCode": "0", "ResultDesc": "The service request is processed successfully."}
              Example pending:  {"errorCode": "500.001.1001", "errorMessage": "The transaction is being processed"}
              Example failure:  {"ResultCode": "1032", "ResultDesc": "Request cancelled by user"}

    Raises:
        requests.HTTPError: on non-2xx HTTP response that isn't a known Daraja error body.
    """
    sc = shortcode or settings.MPESA_SHORTCODE
    pk = passkey or settings.MPESA_PASSKEY

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{sc}{pk}{timestamp}".encode()
    ).decode()

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "BusinessShortCode": sc,
        "Password":          password,
        "Timestamp":         timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
        json=payload,
        headers=headers,
        timeout=15,
    )

    logger.debug(
        "STK query %s → HTTP %s: %s",
        checkout_request_id, response.status_code, response.text,
    )

    # Safaricom returns 200 even for "still processing" errors, but
    # returns 4xx/5xx for auth and other server-side errors.
    # Raise only for genuine HTTP errors, not for Daraja-level errors
    # which come back as 200 with an errorCode body.
    if response.status_code >= 500:
        response.raise_for_status()

    return response.json()
