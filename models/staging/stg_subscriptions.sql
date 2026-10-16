select
    id as subscription_id,
    {{ json_text('payload', '$.customer') }} as customer_id,
    {{ json_text('payload', '$.status') }} as status,
    lower({{ json_text('payload', '$.currency') }}) as currency,
    {{ unix_to_utc(json_text('payload', '$.created')) }} as created_at,
    {{ unix_to_utc(json_text('payload', '$.start_date')) }} as start_at,
    {{ unix_to_utc(json_text('payload', '$.canceled_at')) }} as canceled_at,
    {{ unix_to_utc(json_text('payload', '$.cancel_at')) }} as cancel_at
from {{ source('raw', 'raw_subscriptions') }}
