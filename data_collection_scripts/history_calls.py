import functions_framework
import requests
import datetime
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import time


def get_key(domain, token):
    # ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ТОКЕНА
    url = f"https://api2.onlinepbx.ru/{domain}/auth.json"

    data = {
        "auth_key": token,
        "new": "true"
    }

    print("➡️ Запрос на получение ключей")

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


def get_history_of_calls(date_start, date_end, domain, key, key_id):
    # ФУНКЦИЯ ДЛЯ СБОРА ДАННЫХ О ЗВОНКАХ
    try:
        print("🚀 Запрос истории звонков")
        print(f"📅 Период: {date_start} → {date_end}")

        url = f"https://api2.onlinepbx.ru/{domain}/mongo_history/search.json"

        data = {
            "start_stamp_from": int(date_start.timestamp()),
            "start_stamp_to": int(date_end.timestamp())
        }

        headers = {"X-PBX-AUTHENTICATION": f"{key_id}:{key}"}


        response = requests.post(url, headers=headers, data=data)

        print(f"🌐 Статус ответа: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ Ошибка API:", response.text)
            return pd.DataFrame()

        response_json = response.json()

        calls = response_json.get("data", [])

        print(f"📞 Получено звонков: {len(calls)}")

        if not calls:
            print("⚠️ Нет данных")
            return pd.DataFrame()

        df = pd.DataFrame(calls)

        print(f"📊 Колонки до обработки: {list(df.columns)}")

        # переименование + выбор колонок
        df = df.rename(columns={
            "uuid": "call_id",
            "accountcode": "direction",
            "caller_id_number": "caller",
            "destination_number": "callee",
            "from_host": "from_domain",
            "to_host": "to_domain",
            "gateway": "gateway",
            "end_stamp": "date",
            "duration": "call_duration",
            "user_talk_time": "dialog_duration",
            "hangup_cause": "hangup_cause",
        })[
            [
                "call_id",
                "direction",
                "caller",
                "callee",
                "from_domain",
                "to_domain",
                "gateway",
                "date",
                "call_duration",
                "dialog_duration",
                "hangup_cause"
            ]
        ]

        print("✅ Данные подготовлены")

        return df

    except Exception as e:
        import traceback
        print("🔥 Ошибка в get_history_of_calls:", e)
        print(traceback.format_exc())
        return pd.DataFrame()
        

def upload_to_bigquery(data, project_id, table_id, mode):
    # ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ ДАННЫХ В BQ
    try:
        print("🚀 Начинаю загрузку в BigQuery")

        if data.empty:
            print("⚠️ DataFrame пуст — загрузка отменена")
            return

        client = bigquery.Client()

        if mode == "append":
            write_mode = "WRITE_APPEND"
        elif mode == "truncate":
            write_mode = "WRITE_TRUNCATE"
        else:
            raise ValueError("mode должен быть append или truncate")

        print(f"📦 Режим: {mode}")
        print(f"📊 Строк: {len(data)}")
        job_config = bigquery.LoadJobConfig(write_disposition=write_mode)

        job = client.load_table_from_dataframe(
            data,
            table_id,
            job_config=job_config
        )
        job.result()

        print("✅ Загрузка завершена")

    except Exception as e:
        import traceback
        print("🔥 Ошибка при загрузке в BQ:", e)
        print(traceback.format_exc())
        

# ===== Cloud Run entrypoint =====
@functions_framework.http
def sync_http(request):
    try:
        # ===== настройки =====
        domain = "YOUR_DOMAIN.onpbx.ru"
        token = "YOUR_TOKEN"
        project="YOUR_PROJECT_ID"
        table_id = "YOUR_TABLE_ID"
        mode = "truncate"    # append или truncate
        start = datetime.datetime(2026, 1, 1)
        end = datetime.datetime(2026, 4, 16)

        # ======= main ========
        print("🏁 Старт скрипта")

        key, key_id = get_key(domain=domain, token=token)

        all_data = []
        current_start = start

        while current_start < end:
            current_end = min(current_start + datetime.timedelta(days=7), end)

            print(f"📅 Запрос: {current_start} → {current_end}")

            df = get_history_of_calls(
                date_start=current_start,
                date_end=current_end,
                domain=domain,
                key=key,
                key_id=key_id
            )

            if not df.empty:
                all_data.append(df)

            current_start = current_end
            time.sleep(1)

        if all_data:
            data = pd.concat(all_data, ignore_index=True)
            data = data.drop_duplicates(subset=["call_id"])
        else:
            data = pd.DataFrame()

        print("📊 Итоговые колонки:", list(data.columns))

        upload_to_bigquery(data=data, project_id=project, table_id=table_id, mode=mode)

        print("🏁 Скрипт завершён")

        return f"OK: {len(data)} rows", 200

    except Exception as e:
        print("❌ ОШИБКА:", str(e))
        return f"Ошибка: {str(e)}", 500
    
