import hashlib
from urllib.parse import urlencode

import requests

from . import app_settings


class DragonpayClient:
    def __init__(self):
        self.api = app_settings.DRAGONPAY_API
        self.ccy = app_settings.DRAGONPAY_TRANSACTION_CCY
        self.description = "test payment"
        self.email = app_settings.DRAGONPAY_TRANSACTION_EMAIL

    def create_payment(
        self,
        amount,
        transaction_id,
        proc_id=None,
        merchant_id=None,
        merchant_password=None,
    ):
        signature = self.generate_signature(
            amount,
            transaction_id,
            merchant_id=merchant_id,
            merchant_password=merchant_password,
        )
        qs_data = {
            "merchantid": merchant_id,
            "txnid": transaction_id,
            "amount": amount,
            "ccy": self.ccy,
            "description": self.description,
            "email": self.email,
            "digest": signature,
        }
        if proc_id:
            qs_data["procId"] = proc_id
        query_string = urlencode(qs_data)
        url = f"{self.api}?{query_string}"
        return url

    def generate_signature(
        self, amount, transaction_id, merchant_id=None, merchant_password=None
    ):
        values = [
            merchant_id,
            transaction_id,
            amount,
            self.ccy,
            self.description,
            self.email,
            merchant_password,
        ]
        string = ":".join(values)
        hash_obj = hashlib.sha1(string.encode())
        return hash_obj.hexdigest()


class BukasClient:
    def __init__(self):
        self.api = app_settings.BUKAS_API
        self.api_key = app_settings.BUKAS_API_KEY
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def create_payment(self, data):
        payload = {k: data[k] for k in sorted(data)}
        generated_string = ":".join([str(value) for value in payload.values()])
        generated_sha = hashlib.sha512(generated_string.encode()).hexdigest()

        payload.update(
            {
                "digest": generated_sha,
                "api_key": self.api_key,
            }
        )
        query_string = urlencode({"api_key": self.api_key})
        url = f"{self.api}?{query_string}"

        response = requests.post(url, json=payload, headers=self.headers)
        return response
