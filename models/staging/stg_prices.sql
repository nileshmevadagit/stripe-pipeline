select
    id as price_id,
    json_extract_string(payload, '$.product') as product_id,
    lower(json_extract_string(payload, '$.currency')) as currency,
    cast(json_extract_string(payload, '$.unit_amount') as bigint) as unit_amount,
    json_extract_string(payload, '$.recurring.interval') as billing_interval,
    cast(json_extract_string(payload, '$.recurring.interval_count') as integer) as interval_count,
    cast(json_extract_string(payload, '$.active') as boolean) as active,
    {{ unix_to_utc("json_extract_string(payload, '$.created')") }} as created_at
from {{ source('raw', 'raw_prices') }}
