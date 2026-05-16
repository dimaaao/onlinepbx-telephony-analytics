with
raw_webhook_data as (select * from `YOUR_PROJECT_ID.raw_telephony`),
raw_history_data as (select * from `YOUR_PROJECT_ID.raw_history`),
dict_managers as (select dt, num, name as manager from `YOUR_PROJECT_ID.dict_managers`),

union_table as (
  select * except(date, call_duration, dialog_duration),
    DATETIME(TIMESTAMP_SECONDS(SAFE_CAST(date AS INT64)), "Asia/Almaty") AS dt,
    SAFE_CAST(call_duration AS INT64) as call_duration,
    SAFE_CAST(dialog_duration AS INT64) as dialog_duration
  from raw_webhook_data

  UNION ALL BY NAME

  select * except(date, call_duration, dialog_duration),
DATETIME(TIMESTAMP_SECONDS(SAFE_CAST(date AS INT64)), "Asia/Almaty") AS dt,
    SAFE_CAST(call_duration AS INT64) as call_duration,
    SAFE_CAST(dialog_duration AS INT64) as dialog_duration,
    null as download_url
  from raw_history_data
),

removing_duplicates as (
  select * from union_table
    QUALIFY ROW_NUMBER() OVER (PARTITION BY call_id ORDER BY dt ASC) = 1
),

final_table as (
  select 
    *,
    call_duration - dialog_duration AS wait_time,
    DATE(dt) as dt_for_table,
    1 as num_of_calls,
    case when dialog_duration > 0 then 1 else 0 end as num_of_answered_calls,
    case when dialog_duration >= 90 then 1 else 0 end as num_of_success_calls
  from removing_duplicates 
   where direction != 'inbound'
),

first_snapshot as (
  select * from dict_managers
  QUALIFY ROW_NUMBER() OVER (PARTITION BY num ORDER BY dt ASC) = 1
)

select 
  f.*,
  coalesce(m.manager, fs.manager) as manager
from final_table f
left join dict_managers m on f.caller = m.num and DATE(f.dt) = m.dt
left join first_snapshot fs on f.caller = fs.num
