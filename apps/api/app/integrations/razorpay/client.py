import base64
import hashlib
import secrets
import time
from typing import Any, Optional

import httpx

from app.config import settings


class RazorpayClientError(Exception):
    pass


class RazorpayAuthError(RazorpayClientError):
    pass


class RazorpayClient:
    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.key_id = key_id if key_id is not None else settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret if key_secret is not None else settings.RAZORPAY_KEY_SECRET
        self.timeout = timeout if timeout is not None else settings.RAZORPAY_TIMEOUT_SECONDS
        self.base_url = "https://api.razorpay.com/v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def _auth_header(self) -> dict:
        creds = f"{self.key_id}:{self.key_secret}"
        token = base64.b64encode(creds.encode()).decode()
        return {"Authorization": f"Basic {token}"}

    async def _request(self, method: str, path: str, params: Optional[dict] = None) -> dict:
        if not self.is_configured:
            raise RazorpayAuthError("Razorpay credentials not configured")

        url = f"{self.base_url}{path}"
        headers = {**self._auth_header(), "Content-Type": "application/json"}
        max_retries = settings.RAZORPAY_MAX_RETRIES
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, params=params, headers=headers)
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2**attempt) + secrets.randbelow(200) / 1000
                            time.sleep(delay)
                            continue
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (500, 502, 503, 504) and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)
                    continue
                if e.response.status_code == 401:
                    raise RazorpayAuthError("Invalid Razorpay credentials")
                raise RazorpayClientError(f"Razorpay API error {e.response.status_code}: {e.response.text[:500]}") from e
            except httpx.TransportError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    time.sleep(delay)
                    continue
                raise RazorpayClientError(f"Razorpay transport error: {str(e)}") from e

        raise RazorpayClientError("Max retries exceeded for Razorpay request")

    async def get_payments(self, from_ts: Optional[int] = None, to_ts: Optional[int] = None, count: int = 100, skip: int = 0) -> list[dict]:
        params: dict[str, Any] = {"count": count, "skip": skip}
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
        data = await self._request("GET", "/payments", params=params)
        return data.get("items", [])

    async def get_orders(self, count: int = 100, skip: int = 0) -> list[dict]:
        params = {"count": count, "skip": skip}
        data = await self._request("GET", "/orders", params=params)
        return data.get("items", [])

    async def get_settlements(self, skip: int = 0, count: int = 100) -> list[dict]:
        params = {"count": count, "skip": skip}
        data = await self._request("GET", "/settlements", params=params)
        return data.get("items", [])

    async def get_settlement_recon(self, settlement_id: str) -> list[dict]:
        data = await self._request("GET", f"/settlements/{settlement_id}/recon")
        return data.get("items", [])
