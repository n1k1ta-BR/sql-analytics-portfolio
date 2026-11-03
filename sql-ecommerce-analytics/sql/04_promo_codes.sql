WITH order_promo AS (
  select DISTINCT order_id, promo_code, SUM(quantity * price) OVER(PARTITION BY order_id) AS revenue
  FROM orders o JOIN order_items oi using(order_id)
  WHERE promo_code IS NOT NULL AND o.status= 'paid'
),

avgcheck_count_revenue AS (
  select DISTINCT promo_code, COUNT(order_id) OVER(PARTITION BY promo_code) AS paid_orders, SUM(revenue) OVER(PARTITION BY promo_code) AS revenue, AVG(revenue) OVER(PARTITION BY promo_code) AS avg_order_value
  FROM order_promo
)

select * FROM avgcheck_count_revenue
WHERE paid_orders >19;
