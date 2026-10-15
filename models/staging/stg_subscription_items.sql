-- Reads the Parquet written by flatten_items. Each date folder is a full snapshot of all
-- subscription items, so only the newest snapshot is used. Reading every folder would
-- count each item once per run date.
with silver as (
    select
        subscription_id,
        item_id,
        price_id,
        cast(quantity as bigint) as quantity,
        cast(dt as date) as dt
    from read_parquet('data/silver/subscription_items/*/*.parquet')
)
select *
from silver
where dt = (select max(dt) from silver)
