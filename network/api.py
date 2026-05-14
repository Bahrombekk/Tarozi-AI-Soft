from __future__ import annotations
import base64
import os
import socket
import warnings
from urllib.parse import urlparse

import cv2
import numpy as np
import requests
import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

from core.config import log, timeout, get_token_url, URL_NOT_FOUND, base_url
from core.cipher import Cipher

cipher = Cipher()


def login(url: str, data: dict) -> tuple[bool, dict]:
    try:
        if os.path.exists("settings/tkn.bin"):
            os.remove("settings/tkn.bin")

        response = requests.post(
            url=url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        try:
            js = response.json()
        except Exception:
            js = response.text
        if response.status_code in (200, 201):
            token = js.get("data", {}).get("token", {}).get("access", URL_NOT_FOUND)
            cipher.write(file_path="settings/tkn.bin", data=[token])
            log(message=f"[api.login] Response: {js}", level="INFO")
            return True, js
        log(message=f"[api.login] {js}", level="INFO")
        return False, {"response": js}
    except Exception as err:
        log(message=f"[api.login] {err}", level="ERROR")
        return False, {"response": str(err)}


def check_server(domain_name: str = base_url, tt: int = 3) -> bool:
    for port in (443, 80):
        try:
            socket.setdefaulttimeout(tt)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((domain_name, port))
            sock.close()
            return True
        except (socket.timeout, socket.error):
            continue
    return False


def check_internet_connection() -> bool:
    try:
        response = requests.get(url="https://google.com", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def get_token(data: dict, login_url: str | None = None) -> str:
    token = "TOKEN_OLINMADI"
    _login_url = login_url or get_token_url
    try:
        tokens = cipher.read_bin_file(file_path="settings/tkn.bin")
        if tokens:
            return str(tokens[0]).strip()
        log(message="Token Not Found settings/tkn.bin", level="WARNING")
        login(url=_login_url, data=data)
        tokens = cipher.read_bin_file(file_path="settings/tkn.bin")
        if tokens:
            return str(tokens[0]).strip()
    except Exception as err:
        log(message=f"[api.get_token] {err}")
    return token


def refresh_token(data: dict, login_url: str | None = None) -> str:
    """Kesh tokenni o'chirib, serverdan yangi token oladi (401 bo'lganda ishlatiladi)."""
    try:
        if os.path.exists("settings/tkn.bin"):
            os.remove("settings/tkn.bin")
    except Exception as err:
        log(message=f"[api.refresh_token] tkn.bin o'chirishda xato: {err}")
    return get_token(data=data, login_url=login_url)


def image_to_base64(img: np.ndarray | None) -> str | None:
    try:
        if not isinstance(img, np.ndarray):
            return None
        _, buffer = cv2.imencode(".jpg", img)
        return base64.b64encode(buffer).decode("utf-8")
    except Exception:
        return None


def get_base_url(url: str = get_token_url) -> str:
    parsed = urlparse(url)
    return parsed.netloc


def ping(station_code: str, ping_url: str | None = None,
         com_port_status: str | None = None) -> bool:
    from requests.adapters import HTTPAdapter
    urls = (
        [ping_url] if ping_url
        else [
            f"https://{base_url}/api/wagon-scale-values/ping",
            f"http://{base_url}/api/wagon-scale-values/ping",
        ]
    )
    for url in urls:
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=0))
        session.mount("http://",  HTTPAdapter(max_retries=0))
        try:
            payload = {"stationCode": str(station_code)}
            if com_port_status is not None:
                payload["comPortStatus"] = str(com_port_status)
            response = session.post(
                url=url,
                json=payload,
                headers={"Content-Type": "application/json", "Connection": "close"},
                timeout=8,
                verify=False,
            )
            log(message=f"[api.ping] status={response.status_code} stationCode={station_code} "
                        f"comPortStatus={com_port_status}", level="INFO")
            return response.status_code in (200, 201)
        except Exception as err:
            log(message=f"[api.ping] {url}: {err}", level="WARNING")
        finally:
            session.close()
    return False
