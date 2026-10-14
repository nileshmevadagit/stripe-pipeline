-- Monthly recurring revenue now, per currency, in smallest units.
-- Counts subscriptions with status active or trialing.
select
    currency,
    sum(monthly_amount_minor) as mrr_minor,
    count(distinct subscription_id) as active_subscriptions
from {{ ref('fct_subscription_items') }}
where subscription_status in ('active', 'trialing')
group by currency
