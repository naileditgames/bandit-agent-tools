import uuid
import requests


def create_user(token: str, server_id: str, axiom_name: str) -> dict:
    url = (
        f"https://api5-rhel1-{axiom_name}.installprogram.eu"
        f"/casino/user/public/v1/accounts/login/token"
        f"?fields=core%2Cbalance%2Csession"
    )
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Origin": f"https://mobile-app1-{axiom_name}.installprogram.eu",
        "Referer": f"https://mobile-app1-{axiom_name}.installprogram.eu/",
        "X-ClientTypeId": "40",
        "X-CorrelationId": str(uuid.uuid4()),
    }
    payload = {
        "sessionProductId": server_id,
        "numLaunchTokens": 10,
        "environment": {
            "clientTypeId": 40,
            "languageCode": "en",
        },
        "deviceAttributes": [
            {"shortCode": "bn", "value": "Apple"},
            {"shortCode": "dos", "value": "OS X"},
            {"shortCode": "dosv", "value": "26.1.0"},
            {"shortCode": "it", "value": "false"},
            {"shortCode": "mktn", "value": ""},
            {"shortCode": "mbb", "value": "Chrome"},
            {"shortCode": "mbbv", "value": "142.0.7444.176"},
            {"shortCode": "mdln", "value": ""},
            {"shortCode": "ua", "value": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"},
            {"shortCode": "ff", "value": "desktop"},
        ],
        "token": token,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
