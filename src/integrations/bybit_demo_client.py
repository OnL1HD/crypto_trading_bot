from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
import hashlib
import hmac
import json
from time import time
from urllib.parse import urlencode

import requests


BYBIT_DEMO_DEFAULT_BASE_URL = 'https://api-demo.bybit.com'
BYBIT_RECV_WINDOW = '5000'


class BybitDemoClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstrumentConstraints:
    min_qty: Decimal
    max_qty: Decimal
    qty_step: Decimal


@dataclass(frozen=True)
class OrderResult:
    order_id: str | None
    ret_code: str
    ret_msg: str


@dataclass(frozen=True)
class BybitDemoClient:
    api_key: str
    api_secret: str
    base_url: str = BYBIT_DEMO_DEFAULT_BASE_URL
    timeout_seconds: float = 10.0

    def _build_signature(self, timestamp_ms: str, payload: str) -> str:
        raw = f'{timestamp_ms}{self.api_key}{BYBIT_RECV_WINDOW}{payload}'
        return hmac.new(
            self.api_secret.encode('utf-8'),
            raw.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        signed: bool = False,
        allowed_ret_codes: set[int] | None = None,
    ) -> dict:
        url = f'{self.base_url}{path}'
        headers = {'Content-Type': 'application/json'}
        request_params = params or {}
        body_payload = body or {}
        serialized_body = json.dumps(body_payload) if method.upper() != 'GET' else None

        if signed:
            timestamp_ms = str(int(time() * 1000))
            payload = (
                urlencode(sorted(request_params.items()))
                if method.upper() == 'GET'
                else serialized_body or ''
            )
            headers.update(
                {
                    'X-BAPI-API-KEY': self.api_key,
                    'X-BAPI-TIMESTAMP': timestamp_ms,
                    'X-BAPI-RECV-WINDOW': BYBIT_RECV_WINDOW,
                    'X-BAPI-SIGN': self._build_signature(timestamp_ms, payload),
                }
            )

        response = requests.request(
            method=method.upper(),
            url=url,
            params=request_params or None,
            data=serialized_body,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        ret_code = int(payload.get('retCode', -1))
        if ret_code != 0 and (allowed_ret_codes is None or ret_code not in allowed_ret_codes):
            raise BybitDemoClientError(
                f"Bybit demo API error ({ret_code}): {payload.get('retMsg', 'Unknown error')}"
            )
        return payload

    def get_server_time(self) -> dict:
        return self._request('GET', '/v5/market/time')

    def get_ticker(self, *, category: str, symbol: str) -> dict:
        payload = self._request(
            'GET',
            '/v5/market/tickers',
            params={'category': category, 'symbol': symbol},
        )
        result = payload.get('result', {})
        items = result.get('list', [])
        if not items:
            raise BybitDemoClientError(f'No ticker returned for {category} {symbol}')
        return items[0]

    def get_instrument_constraints(self, *, category: str, symbol: str) -> InstrumentConstraints:
        payload = self._request(
            'GET',
            '/v5/market/instruments-info',
            params={'category': category, 'symbol': symbol},
        )
        result = payload.get('result', {})
        items = result.get('list', [])
        if not items:
            raise BybitDemoClientError(f'No instrument info returned for {category} {symbol}')

        lot_filter = items[0].get('lotSizeFilter', {})
        try:
            return InstrumentConstraints(
                min_qty=Decimal(str(lot_filter['minOrderQty'])),
                max_qty=Decimal(str(lot_filter['maxOrderQty'])),
                qty_step=Decimal(str(lot_filter['qtyStep'])),
            )
        except KeyError as exc:
            raise BybitDemoClientError(f'Instrument info missing quantity constraints for {symbol}') from exc

    def set_leverage(self, *, category: str, symbol: str, leverage: int) -> dict:
        return self._request(
            'POST',
            '/v5/position/set-leverage',
            body={
                'category': category,
                'symbol': symbol,
                'buyLeverage': str(leverage),
                'sellLeverage': str(leverage),
            },
            signed=True,
            allowed_ret_codes={110043},
        )

    def create_market_order(
        self,
        *,
        category: str,
        symbol: str,
        side: str,
        qty: Decimal,
        reduce_only: bool = False,
    ) -> OrderResult:
        body = {
            'category': category,
            'symbol': symbol,
            'side': side,
            'orderType': 'Market',
            'qty': self.format_decimal(qty),
            'positionIdx': 0,
            'reduceOnly': reduce_only,
        }
        payload = self._request('POST', '/v5/order/create', body=body, signed=True)
        result = payload.get('result', {})
        return OrderResult(
            order_id=result.get('orderId'),
            ret_code=str(payload.get('retCode', '0')),
            ret_msg=str(payload.get('retMsg', 'OK')),
        )

    def get_positions(self, *, category: str, symbol: str | None = None, settle_coin: str | None = None) -> list[dict]:
        params: dict[str, str] = {'category': category}
        if symbol:
            params['symbol'] = symbol
        if settle_coin:
            params['settleCoin'] = settle_coin
        payload = self._request('GET', '/v5/position/list', params=params, signed=True)
        result = payload.get('result', {})
        items = result.get('list', [])
        if not isinstance(items, list):
            raise BybitDemoClientError('Unexpected position response payload from Bybit demo API')
        return items

    @staticmethod
    def quantize_quantity(raw_qty: Decimal, constraints: InstrumentConstraints) -> Decimal:
        if raw_qty <= 0:
            return Decimal('0')
        if constraints.qty_step <= 0:
            return raw_qty

        steps = (raw_qty / constraints.qty_step).quantize(Decimal('1'), rounding=ROUND_DOWN)
        normalized = steps * constraints.qty_step
        if normalized < constraints.min_qty:
            return Decimal('0')
        if normalized > constraints.max_qty:
            return constraints.max_qty
        return normalized

    @staticmethod
    def format_decimal(value: Decimal) -> str:
        normalized = value.normalize()
        text = format(normalized, 'f')
        if '.' in text:
            text = text.rstrip('0').rstrip('.')
        return text or '0'
