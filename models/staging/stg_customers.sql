-- Keeps only the allowlisted fields. Name, email, phone and address lines are dropped.
select
    c.id as customer_id,
    k.customer_key,
    {{ json_text('c.payload', '$.address.country') }} as country,
    {{ unix_to_utc(json_text('c.payload', '$.created')) }} as created_at,
    cast({{ json_text('c.payload', '$.livemode') }} as boolean) as livemode
from {{ source('raw', 'raw_customers') }} c
left join {{ source('raw', 'customer_keys') }} k on k.customer_id = c.id
