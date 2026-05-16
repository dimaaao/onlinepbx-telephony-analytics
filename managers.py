import requests
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account


def get_key(domain, token):
    
    url = f"https://api2.onlinepbx.ru/{domain}/auth.json"

    data = {
        "auth_key": token,
        "new": "true"
    }

    response = requests.post(url=url, data=data)

    result = response.json()

    data_block = result.get("data", {})

    key = data_block.get("key")
    key_id = data_block.get("key_id")

    if not key or not key_id:
        raise Exception(f"Не удалось получить ключи: {result}")
    
    return key, key_id

def get_managers(domain, key, key_id,):
    
    url = f"https://api2.onlinepbx.ru/{domain}/user/get.json"

    headers = {
    "X-PBX-AUTHENTICATION": f"{key_id}:{key}"
    }

    response = requests.post(url, headers=headers)

    data = response.json().get("data", [])

    df = pd.DataFrame(data)
    
    return df

# ===== настройки =====
domain = "pbx28683.onpbx.ru"
token = "cWU3UEFmcDc5QnNHRTVFamR4YUZCNklaYnRGUTE5aHU"

# ====== main ======
key, key_id = get_key(domain, token)
data = get_managers(domain=domain, key=key, key_id=key_id)

print(data.columns)
