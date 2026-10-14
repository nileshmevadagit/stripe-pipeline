select
    id as invoice_id,
    json_extract_string(payload, '$.customer') as customer_id,
    json_extract_string(payload, '$.status') as status,
    lower(json_extract_string(payload, '$.currency')) as currency,
    cast(json_extract_string(payload, '$.amount_paid') as bigint) as amount_paid,
    {{ unix_to_utc("json_extract_string(payload, '$.created')") }} as created_at,
    {{ unix_to_utc("json_extract_string(payload, '$.status_transitions.paid_at')") }} as paid_at
from {{ source('raw', 'raw_invoices') }}
