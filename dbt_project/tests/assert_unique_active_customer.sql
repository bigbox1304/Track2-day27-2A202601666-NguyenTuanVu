-- At most one active dimension row may participate in the revenue join.
select customer_id, count(*) as active_rows
from {{ ref('stg_customers') }}
where is_active = true
group by customer_id
having count(*) > 1
