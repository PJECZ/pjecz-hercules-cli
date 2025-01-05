"""
Authentications
"""

import os

import requests
from dotenv import load_dotenv

from lib.exceptions import MyAuthenticationError

# Cargar las variables de entorno
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
TIMEOUT = int(os.getenv("TIMEOUT"))


def get_auth_token() -> str:
    """Hacer el login en la API para obtener el token"""
    payload = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }
    try:
        response = requests.post(
            url=f"{API_BASE_URL}/token",
            data=payload,
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as error:
        raise MyAuthenticationError(error)
    return response.json()["access_token"]
