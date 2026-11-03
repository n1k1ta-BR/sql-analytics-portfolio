SELECT DISTINCT u.user_id, u.channel
FROM users u
JOIN orders o USING(user_id)
JOIN order_items oi USING(order_id)
WHERE o.status = 'paid'
  AND o.order_date >= '2024-05-01'
  AND o.order_date <  '2024-06-01';
