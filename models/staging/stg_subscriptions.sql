select
    id as subscription_id,
    json_extract_string(payload, '$.customer') as customer_id,
    json_extract_string(payload, '$.status') as status,
    lower(json_extract_string(payload, '$.currency')) as currency,
    {{ unix_to_utc("json_extract_string(payload, '$.created')") }} as created_at,
    {{ unix_to_utc("json_extract_string(payload, '$.start_date')") }} as start_at,
    {{ unix_to_utc("json_extract_string(payload, '$.canceled_at')") }} as canceled_at,
    {{ unix_to_utc("json_extract_string(payload, '$.cancel_at')") }} as cancel_at
from {{ source('raw', 'raw_subscriptions') }}
