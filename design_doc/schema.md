# Schema: entity relationship diagram

Built from the dbt models as they are in V1. Staging and marts are shown here. The raw tables
(`raw_<endpoint>`) keep each Stripe object as text in `payload`, so they are not drawn.
Personal fields (name, email, phone, address lines) are not in staging, so they do not appear.

![Schema diagram](schema.png)

Arrows mean "one to many": one customer has many subscriptions, and so on.

```mermaid
erDiagram
    stg_customers ||--o{ stg_subscriptions : "customer_id"
    stg_customers ||--o{ stg_invoices : "customer_id"
    stg_customers ||--o| customer_keys : "customer_key"
    stg_subscriptions ||--o{ stg_subscription_items : "subscription_id"
    stg_prices ||--o{ stg_subscription_items : "price_id"
    stg_products ||--o{ stg_prices : "product_id"
    stg_subscription_items ||--|| fct_subscription_items : "item_id"
    stg_subscriptions ||--o{ fct_subscription_items : "subscription_id"

    stg_customers {
        varchar customer_id PK
        varchar customer_key "HMAC of email"
        varchar country
        timestamp created_at "UTC"
        boolean livemode
    }
    customer_keys {
        varchar customer_id PK
        varchar customer_key
    }
    stg_products {
        varchar product_id PK
        varchar product_name
        boolean active
        timestamp created_at "UTC"
    }
    stg_prices {
        varchar price_id PK
        varchar product_id FK
        varchar currency "lower case"
        bigint unit_amount "smallest unit"
        varchar billing_interval "month or year"
        integer interval_count
        boolean active
        timestamp created_at "UTC"
    }
    stg_subscriptions {
        varchar subscription_id PK
        varchar customer_id FK
        varchar status
        varchar currency "lower case"
        timestamp created_at "UTC"
        timestamp start_at "UTC"
        timestamp canceled_at "UTC"
        timestamp cancel_at "UTC"
    }
    stg_subscription_items {
        varchar item_id PK
        varchar subscription_id FK
        varchar price_id FK
        bigint quantity
        date dt "run date"
    }
    stg_invoices {
        varchar invoice_id PK
        varchar customer_id FK
        varchar status
        varchar currency "lower case"
        bigint amount_paid "smallest unit"
        timestamp created_at "UTC"
        timestamp paid_at "UTC"
    }
    fct_subscription_items {
        varchar item_id PK
        varchar subscription_id FK
        varchar customer_id FK
        varchar subscription_status
        varchar currency
        varchar price_id FK
        varchar product_id FK
        varchar billing_interval
        integer interval_count
        bigint quantity
        decimal monthly_amount_minor
    }
```

## Marts (aggregates, no row-level personal data)

| Mart | Grain | Built from |
|---|---|---|
| `mart_mrr` | one row per currency | `fct_subscription_items`, active and trialing only |
| `mart_active_subscriptions_by_plan` | product, price, currency, interval | `fct_subscription_items` |
| `mart_revenue_by_month` | UTC month of payment, currency | `stg_invoices` (status `paid`), with `currency_decimals` |
| `mart_cancellations_by_month` | UTC month of cancellation, currency | `stg_subscriptions` |

`currency_decimals` (a seed, not drawn) maps each currency to its decimal places.
