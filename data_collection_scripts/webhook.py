import functions_framework
from google.cloud import bigquery
from datetime import datetime
import json

client = bigquery.Client()
TABLE_ID = "YOUR_TABLE_ID"
LOGS_TABLE = "YOUR_TABLE_ID" 


@functions_framework.http
def webhook(request):
    try:
        print("Запрос получен")

        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()


        log_row = {
            "received_at": datetime.now().isoformat(),
            "payload": json.dumps(data or {})
        }

        log_errors = client.insert_rows_json(LOGS_TABLE, [log_row])

        if log_errors:
            print("Ошибка логов:", log_errors)
        else:
            print("Лог записан")

        if not data:
            print("Пустой payload")
            return ("ok", 200)

        print("Payload:", data)

        event_type = data.get("event")

        # фильтр событий
        if event_type != "call_end":
            print(f"Игнор события: {event_type}")
            return ("ok", 200)

        call_id = data.get("uuid")

        if not call_id:
            print("Нет id — пропуск")
            return ("ok", 200)

        # формируем строку
        row = {
            "call_id": call_id,
            "direction": data.get("direction"),
            "caller": data.get("caller"),
            "callee": data.get("callee"),
            "from_domain": data.get("from_domain"),
            "to_domain": data.get("to_domain"),
            "gateway": data.get("gateway"),
            "date": data.get("date"),
            "call_duration": data.get("call_duration"),
            "dialog_duration": data.get("dialog_duration"),
            "hangup_cause": data.get("hangup_cause"),
            "download_url": data.get("download_url")
        }

        print("Подготовленная строка:", row)

        # запись в BQ
        errors = client.insert_rows_json(TABLE_ID, [row])

        if errors:
            print("Ошибка записи в BQ:", errors)
        else:
            print(f"Записано: call_id={call_id}")

        return ("ok", 200)

    except Exception as e:
        import traceback
        print("КРИТИЧЕСКАЯ ОШИБКА:", e)
        print(traceback.format_exc())
        return ("ok", 200)
