SELECT u.channel, SUM(oi.quantity * oi.price) AS revenue
FROM order_items oi
JOIN orders o USING(order_id)
JOIN users u USING(user_id)
WHERE o.status = 'paid'
  AND o.order_date >= '2024-01-01'
  AND o.order_date <  '2024-07-01'
GROUP BY u.channel;
