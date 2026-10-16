select
    id as product_id,
    {{ json_text('payload', '$.name') }} as product_name,
    cast({{ json_text('payload', '$.active') }} as boolean) as active,
    {{ unix_to_utc(json_text('payload', '$.created')) }} as created_at
from {{ source('raw', 'raw_products') }}
