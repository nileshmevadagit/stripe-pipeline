{{ config(materialized='table', tags=['public']) }}
-- Paid revenue by UTC day of payment, per currency. Same rules as mart_revenue_by_month.
select
    cast(i.paid_at as date) as revenue_day,
    i.currency,
    sum(i.amount_paid) as paid_minor,
    d.decimal_places,
    {{ round_major('sum(i.amount_paid) / power(10, d.decimal_places)', 'd.decimal_places') }} as paid_major
from {{ ref('stg_invoices') }} i
join {{ ref('currency_decimals') }} d on d.currency = i.currency
where i.status = 'paid'
  and i.paid_at is not null
group by revenue_day, i.currency, d.decimal_places
