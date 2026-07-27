import base64
import re
import requests


def fetch_web_config(axiom_name: str, api_key: str) -> str:
    url = (
        f"https://axiomcore-app1-{axiom_name}.installprogram.eu"
        f"/Manage/Content/FileContent"
        f"?filePath=M%3A%5CMGS_IISWebSites%5CCasino%5CSGIFakeAPI%5CWeb.config"
    )
    response = requests.get(url, headers={"x-api-key": api_key, "Accept": "application/json"})
    response.raise_for_status()
    data = response.json()
    return base64.b64decode(data["dataObject"]["content"]).decode("utf-8")


def upload_web_config(axiom_name: str, api_key: str, web_config: str) -> None:
    url = (
        f"https://axiomcore-app1-{axiom_name}.installprogram.eu"
        f"/Manage/Content/FileContent"
    )
    payload = {
        "displayName": "Web.config",
        "path": "M:\\MGS_IISWebSites\\Casino\\SGIFakeAPI\\Web.config",
        "content": base64.b64encode(web_config.encode("utf-8")).decode("utf-8"),
        "schema": False,
        "schemaPath": None,
        "schemaContent": None,
    }
    response = requests.patch(
        url,
        json=payload,
        headers={"x-api-key": api_key, "Accept": "application/json", "Content-Type": "application/json"},
    )
    response.raise_for_status()


def set_default_currency(web_config: str, currency: str) -> str:
    """Replace the defaultcurrency value in the XML Web.config string."""
    return re.sub(
        r'(<add\s+key="defaultcurrency"\s+value=")[^"]*(")',
        lambda m: f'{m.group(1)}{currency}{m.group(2)}',
        web_config,
    )
