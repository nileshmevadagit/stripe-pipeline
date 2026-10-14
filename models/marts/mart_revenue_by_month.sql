-- Paid revenue by UTC month of payment, per currency.
-- Amounts are in smallest units, and paid_major is the same amount in whole currency units.
select
    cast(date_trunc('month', i.paid_at) as date) as revenue_month,
    i.currency,
    sum(i.amount_paid) as paid_minor,
    d.decimal_places,
    round(sum(i.amount_paid) / power(10, d.decimal_places), d.decimal_places) as paid_major
from {{ ref('stg_invoices') }} i
join {{ ref('currency_decimals') }} d on d.currency = i.currency
where i.status = 'paid'
  and i.paid_at is not null
group by revenue_month, i.currency, d.decimal_places
