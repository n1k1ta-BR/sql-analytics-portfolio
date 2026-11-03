SELECT u.user_id, u.channel
FROM users u
WHERE EXISTS (SELECT 1 from orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.user_id = u.user_id
  AND status = 'paid'
  AND o.order_date >= '2024-05-01'
  AND o.order_date < '2024-06-01'
  );
