import logging
from typing import Tuple
import requests
from django.conf import settings
import hashlib
import hmac
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PaymentProviderError(Exception):
    pass


class PaymentProviderClient:
    """Thin wrapper around a hypothetical third-party payment HTTP API.

    This client expects `PAYMENT_PROVIDER_API_KEY` and optionally
    `PAYMENT_PROVIDER_BASE_URL` to be configured in Django settings.
    """

    def __init__(self, api_key: str = None, base_url: str = None, timeout: int = 10):
        self.api_key = api_key or settings.PAYMENT_PROVIDER_API_KEY
        self.base_url = base_url or settings.PAYMENT_PROVIDER_BASE_URL
        self.timeout = timeout

    # UroPay-specific helpers
    def _uropay_headers(self) -> Dict[str, str]:
        # X-API-KEY + Authorization: Bearer <sha512(secret)>
        secret = getattr(settings, "UROPAY_SECRET", None)
        api_key = getattr(settings, "UROPAY_API_KEY", None)
        if not api_key or not secret:
            raise PaymentProviderError("UroPay API key/secret not configured")
        hashed = hashlib.sha512(secret.encode("utf-8")).hexdigest()
        return {
            "X-API-KEY": api_key.strip(),
            "Authorization": f"Bearer {hashed.strip()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, json: Any = None, params: Dict[str, str] | None = None):
        url = (getattr(settings, "UROPAY_BASE_URL", self.base_url) or self.base_url or "https://api.uropay.me").rstrip("/") + path
        headers = self._uropay_headers()
        try:
            resp = requests.request(method, url, json=json, params=params, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.exception("Payment provider HTTP request failed")
            raise PaymentProviderError("Payment provider unreachable") from exc
        if resp.status_code >= 500:
            logger.error("Provider server error %s: %s", resp.status_code, resp.text)
            raise PaymentProviderError(f"Provider server error: {resp.status_code}")

        # Return parsed JSON for non-5xx; let caller decide on success
        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, {"raw": resp.text}

    def charge(self, amount: str, currency: str, provider_token: str) -> Tuple[bool, str]:
        """Charge the given amount. Returns (success, provider_reference).

        Raises PaymentProviderError on unexpected HTTP failures.
        """
        if not self.api_key:
            raise PaymentProviderError("Payment provider API key not configured")

        url = self.base_url.rstrip("/") + "/charge" if self.base_url else "https://example-payments.local/charge"

        payload = {
            "amount": str(amount),
            "currency": currency,
            "token": provider_token,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Generic charge path retained for non-UroPay providers
        status_code, data = self._request("POST", "/charge", json=payload)
        if status_code == 200 and data.get("success"):
            return True, data.get("reference") or ""
        if status_code == 200:
            return False, data.get("reference") or ""
        raise PaymentProviderError(f"Provider error: {status_code}")

    # UroPay-specific API methods
    def uropay_generate(self, *, vpa: str, vpaName: str, amount_paise: int, merchantOrderId: str, customerName: str, customerEmail: str, transactionNote: str | None = None, notes: dict | None = None) -> Dict[str, Any]:
        payload = {
            "vpa": vpa,
            "vpaName": vpaName,
            "amount": amount_paise,
            "merchantOrderId": merchantOrderId,
            "customerName": customerName,
            "customerEmail": customerEmail,
        }
        if transactionNote:
            payload["transactionNote"] = transactionNote
        if notes:
            payload["notes"] = notes

        status_code, data = self._request("POST", "/order/generate", json=payload)
        if status_code != 200:
            raise PaymentProviderError(f"UroPay generate failed: {status_code}")
        return data.get("data", {})

    def uropay_update(self, *, uroPayOrderId: str, referenceNumber: str, orderStatus: str | None = None) -> Dict[str, Any]:
        payload = {"uroPayOrderId": uroPayOrderId, "referenceNumber": referenceNumber}
        if orderStatus:
            payload["orderStatus"] = orderStatus

        status_code, data = self._request("PATCH", "/order/update", json=payload)
        if status_code != 200:
            print(f"DEBUG: Update failed. Status: {status_code}, Response: {data}")
            raise PaymentProviderError(f"UroPay update failed: {status_code}")
        return data.get("data", {})

    def uropay_status(self, uroPayOrderId: str) -> Dict[str, Any]:
        status_code, data = self._request("GET", f"/order/status/{uroPayOrderId}")
        if status_code != 200:
            raise PaymentProviderError(f"UroPay status failed: {status_code}")
        return data.get("data", {})
