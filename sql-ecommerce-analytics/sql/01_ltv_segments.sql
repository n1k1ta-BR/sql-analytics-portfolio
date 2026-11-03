with users_LTV as(
  select u.user_id, sum(case
  when o.status = 'paid'
  then oi.quantity * oi.price
  else 0
  END
  ) as LTV, count(distinct o.order_id) FILTER(WHERE o.status = 'paid') as paid_orders
  from users u left join orders o using(user_id) left join order_items oi  using(order_id)
  group by u.user_id
),
segments as (select *, case
  WHEN paid_orders = 0 then 'no_paid_orders'
  WHEN paid_orders = 1 then 'one_order'
  WHEN paid_orders BETWEEN 2 AND 3 then '2_3_orders'
  ELSE '4_plus_orders'
  END AS segment
  from users_LTV
  order by segment asc)

select segment, count(user_id) as users, AVG(LTV) AS avg_ltv, sum(LTV) as total_ltv
from segments
group by segment
order by segment;
