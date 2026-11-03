WITH order_prices AS (
  select DISTINCT order_id, user_id, order_date, SUM(quantity * price) OVER(PARTITION BY order_id) AS order_revenue FROM users u JOIN orders o using(user_id) JOIN order_items using(order_id)
WHERE o.status = 'paid'
ORDER BY user_id
),

ranged_orders AS (
select *, ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY order_date, order_id) AS order_number
FROM order_prices),

avg_count AS (
  select *, AVG(order_revenue) OVER(PARTITION BY user_id ORDER BY order_number
  ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prev_avg_revenue from ranged_orders
)
select order_id, user_id, order_date, order_revenue, prev_avg_revenue from avg_count
WHERE order_revenue > 3 * prev_avg_revenue;
