import requests
import urllib
import hmac
import base64
import hashlib
import os
import re

from datetime import datetime


class RESTKrakenResponse:
    def __init__(self, raw_response: requests.models.Response) -> None:
        self._raw_response = raw_response

        # Status codes are generally not used in the Kraken API
        # Either 200 or not meaningful
        self.status_ok = self._raw_response.status_code == 200
        self.status_ok = self.status_ok and not self._raw_response.json()['error']

        self.out_json: dict = None
        if self.status_ok:
            self.out_json = self._raw_response.json()['result']
        else:
            self.out_json = self._raw_response.json()['error']

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(success={self.status_ok}, out_json={self.out_json.__repr__()})"


class RESTKrakenRequest:
    def __init__(self, endpoint: str, method: str, payload: dict = None) -> None:
        self.endpoint = endpoint
        self.payload = payload
        self.method = method.lower()

    def send(self) -> RESTKrakenResponse:
        return RESTKrakenResponse(
            getattr(requests, self.method)(
                url=self.endpoint,
                data=self.payload
            )
        )

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(endpoint={self.endpoint}, "
                f"method={self.method.upper()}, payload={self.payload.__repr__()})")


class RESTKrakenAuthenticatedRequest(RESTKrakenRequest):
    def __init__(self, endpoint: str, method: str, payload: dict = None) -> None:
        super().__init__(endpoint, method, payload)
        self.pk = os.getenv('KRAKEN_PK', None)
        self.api_key = os.getenv('KRAKEN_KEY', None)
        if self.pk is None or self.api_key is None:
            raise RuntimeError(
                "Authenticated requests require the following "
                "environment variables to be set: KRAKEN_PK and KRAKEN_KEY"
            )

    def _get_kraken_signature(self, payload):
        # https://docs.kraken.com/rest/#section/Authentication/Headers-and-Signature
        postdata = urllib.parse.urlencode(payload)
        encoded = (payload['nonce'] + postdata).encode()
        uri_path = re.match(r".+(/0.+)", self.endpoint)[1]
        message = uri_path.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(self.pk), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def _gen_nonce(self) -> int:
        return int(datetime.now().timestamp() * 1e3)
    
    def _gen_auth_headers(self, payload) -> dict:
        api_sign = self._get_kraken_signature(payload)
        return {
            'API-Key': self.api_key,
            'API-Sign': api_sign
        }
    
    def send(self) -> RESTKrakenResponse:
        nonce_dict = { 'nonce': str(self._gen_nonce()) }

        if self.payload is None:
            payload = nonce_dict
        else:
            payload = self.payload
            payload.update(nonce_dict)

        auth_headers = self._gen_auth_headers(payload)
        return RESTKrakenResponse(
            getattr(requests, self.method)(
                url=self.endpoint,
                data=payload,
                headers=auth_headers
            )
        )

class KrakenRESTClient:
    def __init__(
        self,
        base_url: str = "https://api.kraken.com"
    ) -> None:
        self.base_url = base_url

    def system_status(self) -> RESTKrakenResponse:
        return RESTKrakenRequest(
            endpoint=f"{self.base_url}/0/public/SystemStatus",
            method='GET',
        ).send()
    
    def account_balance(self) -> RESTKrakenResponse:
        return RESTKrakenAuthenticatedRequest(
            endpoint=f"{self.base_url}/0/private/Balance",
            method='POST'
        ).send()
