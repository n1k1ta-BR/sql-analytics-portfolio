WITH users_orders AS (
  SELECT DISTINCT user_id, city, COUNT(order_id) OVER(PARTITION BY user_id) AS orders
  FROM orders o JOIN users u using(user_id)
  WHERE o.status = 'paid'
),

total_repeate_rate AS (
  select SUM(CASE WHEN orders >1 THEN 1 ELSE 0 END) AS repeated, COUNT(user_id) as total_users
  FROM users_orders
),

repeated_count as (
  SELECT *, SUM(CASE WHEN orders >1 THEN 1 ELSE 0 END) OVER(PARTITION BY city) AS repeated, COUNT(user_id) OVER(PARTITION BY city) AS total_users
  FROM users_orders
),

repeate_rate AS (
  SELECT DISTINCT rc.city, rc.total_users AS buyers, rc.repeated AS repeat_buyers, rc.repeated *1.0/ rc.total_users AS repeat_rate, trr.repeated * 1.0 / trr.total_users AS overall_repeat_rate
  FROM repeated_count rc CROSS JOIN total_repeate_rate trr
  WHERE rc.repeated * 1.0 / rc.total_users >
          trr.repeated * 1.0 / trr.total_users
)


select * from repeate_rate;
