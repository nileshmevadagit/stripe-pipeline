select
    id as invoice_id,
    {{ json_text('payload', '$.customer') }} as customer_id,
    {{ json_text('payload', '$.status') }} as status,
    lower({{ json_text('payload', '$.currency') }}) as currency,
    cast({{ json_text('payload', '$.amount_paid') }} as bigint) as amount_paid,
    {{ unix_to_utc(json_text('payload', '$.created')) }} as created_at,
    {{ unix_to_utc(json_text('payload', '$.status_transitions.paid_at')) }} as paid_at
from {{ source('raw', 'raw_invoices') }}
