-- One row per subscription item, with its monthly amount in the currency's smallest unit.
-- Yearly prices are divided by 12. Amounts stay per currency; nothing is converted.
select
    i.item_id,
    i.subscription_id,
    s.customer_id,
    s.status as subscription_status,
    s.currency,
    i.price_id,
    p.product_id,
    p.billing_interval,
    p.interval_count,
    i.quantity,
    cast(
        case
            when p.billing_interval = 'month' then p.unit_amount * i.quantity / p.interval_count
            when p.billing_interval = 'year' then p.unit_amount * i.quantity / (12.0 * p.interval_count)
        end
        as decimal(18, 2)
    ) as monthly_amount_minor
from {{ ref('stg_subscription_items') }} i
join {{ ref('stg_subscriptions') }} s on s.subscription_id = i.subscription_id
join {{ ref('stg_prices') }} p on p.price_id = i.price_id
