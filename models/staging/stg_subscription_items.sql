-- Reads the Parquet written by flatten_items. One row per subscription item.
select
    subscription_id,
    item_id,
    price_id,
    cast(quantity as bigint) as quantity,
    cast(dt as date) as dt
from read_parquet('data/silver/subscription_items/*/*.parquet')
