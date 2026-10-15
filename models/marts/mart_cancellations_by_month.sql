{{ config(materialized='table', tags=['public']) }}
-- Subscriptions cancelled, by UTC month of cancellation, per currency.
select
    cast(date_trunc('month', canceled_at) as date) as cancel_month,
    currency,
    count(*) as cancellations
from {{ ref('stg_subscriptions') }}
where canceled_at is not null
group by cancel_month, currency
