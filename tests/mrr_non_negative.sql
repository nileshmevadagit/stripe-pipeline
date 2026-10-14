-- Fails if any currency has negative MRR. Returns rows only when something is wrong.
select *
from {{ ref('mart_mrr') }}
where mrr_minor < 0
