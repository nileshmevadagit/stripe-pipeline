select
    id as price_id,
    {{ json_text('payload', '$.product') }} as product_id,
    lower({{ json_text('payload', '$.currency') }}) as currency,
    cast({{ json_text('payload', '$.unit_amount') }} as bigint) as unit_amount,
    {{ json_text('payload', '$.recurring.interval') }} as billing_interval,
    cast({{ json_text('payload', '$.recurring.interval_count') }} as integer) as interval_count,
    cast({{ json_text('payload', '$.active') }} as boolean) as active,
    {{ unix_to_utc(json_text('payload', '$.created')) }} as created_at
from {{ source('raw', 'raw_prices') }}
