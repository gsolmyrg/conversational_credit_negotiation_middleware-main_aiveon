import os

import requests


class WhatsappClient:
    def __init__(self):
        self._url = os.getenv("EVOLUTION_URL")
        self._token = os.getenv("EVOLUTION_API_KEY")

    @property
    def _headers(self):
        return {
            "apikey": self._token,
            "Content-Type": "application/json",
        }

    def send_text(self, number: str, text: str, delay: int = 1000):
        payload = {
            "number": number,
            "text": text,
            "delay": delay,
        }
        response = requests.post(self._url, headers=self._headers, json=payload)
        return response.json()
