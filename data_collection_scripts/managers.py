import functions_framework
import requests
import pandas as pd
from google.cloud import bigquery
from datetime import datetime


def get_key(domain, token):
    url = f"https://api2.onlinepbx.ru/{domain}/auth.json"

    data = {
        "auth_key": token,
        "new": "true"
    }

    print("Запрос на получение ключей")

    response = requests.post(url=url, data=data, timeout=10)
    print("STATUS AUTH:", response.status_code)

    result = response.json()
    print("Получено")

    data_block = result.get("data", result)

    key = data_block.get("key")
    key_id = data_block.get("key_id")

    if not key or not key_id:
        raise Exception(f"Не удалось получить ключи: {result}")
    
    return key, key_id


def get_managers(domain, key, key_id):
    url = f"https://api2.onlinepbx.ru/{domain}/user/get.json"

    headers = {
        "X-PBX-AUTHENTICATION": f"{key_id}:{key}"
    }

    print("Запрос менеджеров")

    response = requests.post(url, headers=headers, timeout=10)
    print("STATUS MANAGERS:", response.status_code)

    result = response.json()
    print("MANAGERS RESPONSE:", result)

    df = pd.DataFrame(result.get("data", []))

    print("Колонки:", df.columns.tolist())
    print("Строк получено:", len(df))

    return df


# ===== Cloud Run entrypoint =====
@functions_framework.http
def sync_http(request):
    try:
        print("Старт функции")

        domain = "YOUR_DOMAIN.onpbx.ru"
        token = "YOUR_TOKEN"
        TABLE_ID = "YOUR_TABLE_ID"

        
        key, key_id = get_key(domain, token)
        print("Ключи получены")

        df = get_managers(domain, key, key_id)
        df["dt"] = datetime.utcnow().date()

        if df.empty:
            print("DataFrame пустой")
            return "Нет данных", 200

        print("Загружаем в BigQuery")

        client = bigquery.Client()

        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND"
        )

        job = client.load_table_from_dataframe(
            df,
            TABLE_ID,
            job_config=job_config
        )
        job.result()

        print("Загрузка завершена")

        return f"Загружено строк: {len(df)}", 200

    except Exception as e:
        print("ОШИБКА:", str(e))
        return f"Ошибка: {str(e)}", 500
