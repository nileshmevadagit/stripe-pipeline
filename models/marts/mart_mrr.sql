{{ config(materialized='table', tags=['public']) }}
-- Monthly recurring revenue now, per currency, in smallest units.
-- Counts subscriptions with status active or trialing.
select
    m.currency,
    m.mrr_minor,
    round(m.mrr_minor / power(10, d.decimal_places), d.decimal_places) as mrr_major,
    d.decimal_places,
    m.active_subscriptions
from (
    select
        currency,
        sum(monthly_amount_minor) as mrr_minor,
        count(distinct subscription_id) as active_subscriptions
    from {{ ref('fct_subscription_items') }}
    where subscription_status in ('active', 'trialing')
    group by currency
) m
join {{ ref('currency_decimals') }} d on d.currency = m.currency
