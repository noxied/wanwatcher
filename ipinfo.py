"""Minimal ipinfo module for WANwatcher Docker"""

import requests


class Handler:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://ipinfo.io"

    def getDetails(self, ip=None):
        url = f"{self.base_url}/{ip if ip else ''}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        return Details(data)


class Details:
    def __init__(self, data):
        self.ip = data.get("ip")
        self.city = data.get("city")
        self.region = data.get("region")
        self.country = data.get("country")
        self.country_name = data.get("country_name", data.get("country"))
        self.org = data.get("org")
        self.timezone = data.get("timezone")


def getHandler(access_token):
    return Handler(access_token)
