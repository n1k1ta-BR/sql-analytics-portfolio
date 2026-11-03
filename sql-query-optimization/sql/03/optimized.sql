SELECT u.channel, SUM(os.order_revenue) AS revenue
FROM (SELECT order_id, SUM(quantity * price) AS order_revenue FROM order_items GROUP BY order_id) os
JOIN orders o USING(order_id)
JOIN users u USING(user_id)
WHERE o.status = 'paid'
  AND o.order_date >= '2024-01-01'
  AND o.order_date <  '2024-07-01'
GROUP BY u.channel;
