{{ config(materialized='table', tags=['public']) }}
-- Active subscriptions per product and price, per currency.
select
    product_id,
    price_id,
    currency,
    billing_interval,
    count(distinct subscription_id) as active_subscriptions
from {{ ref('fct_subscription_items') }}
where subscription_status in ('active', 'trialing')
group by product_id, price_id, currency, billing_interval
