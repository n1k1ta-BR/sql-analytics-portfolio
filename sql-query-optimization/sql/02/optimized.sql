SELECT user_id, COUNT(*) AS orders
FROM orders
WHERE status = 'paid'
  AND order_date >= '2024-04-01'
  AND order_date <  '2024-07-01'
GROUP BY user_id
HAVING COUNT(*) >= 3;
