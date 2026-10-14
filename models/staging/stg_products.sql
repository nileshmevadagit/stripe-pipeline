select
    id as product_id,
    json_extract_string(payload, '$.name') as product_name,
    cast(json_extract_string(payload, '$.active') as boolean) as active,
    {{ unix_to_utc("json_extract_string(payload, '$.created')") }} as created_at
from {{ source('raw', 'raw_products') }}
