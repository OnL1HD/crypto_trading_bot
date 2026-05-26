from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from time import time
from urllib.parse import urlencode

import requests


BYBIT_MAINNET_BASE_URL = "https://api.bybit.com"
BYBIT_TESTNET_BASE_URL = "https://api-testnet.bybit.com"
BYBIT_RECV_WINDOW = "5000"


@dataclass(frozen=True)
class BybitPrivateClient:
    api_key: str
    api_secret: str
    use_testnet: bool = False
    timeout_seconds: float = 10.0

    @property
    def base_url(self) -> str:
        if self.use_testnet:
            return BYBIT_TESTNET_BASE_URL
        return BYBIT_MAINNET_BASE_URL

    def _build_signature(self, timestamp_ms: str, query_string: str) -> str:
        payload = f"{timestamp_ms}{self.api_key}{BYBIT_RECV_WINDOW}{query_string}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _signed_get(self, path: str, query_params: dict[str, str] | None = None) -> dict:
        params = query_params or {}
        query_string = urlencode(sorted(params.items()))
        timestamp_ms = str(int(time() * 1000))
        signature = self._build_signature(timestamp_ms, query_string)

        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": timestamp_ms,
            "X-BAPI-RECV-WINDOW": BYBIT_RECV_WINDOW,
            "X-BAPI-SIGN": signature,
        }

        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        if payload.get("retCode") != 0:
            ret_code = payload.get("retCode")
            ret_message = payload.get("retMsg", "Unknown Bybit error")
            raise RuntimeError(f"Bybit private API error ({ret_code}): {ret_message}")

        return payload

    def check_account_access(self) -> tuple[bool, str]:
        try:
            self._signed_get("/v5/account/info")
            return True, "Authenticated account check succeeded"
        except requests.RequestException as exc:
            return False, f"Network/HTTP error during account check: {exc}"
        except ValueError as exc:
            return False, f"Invalid response payload during account check: {exc}"
        except Exception as exc:
            return False, str(exc)
