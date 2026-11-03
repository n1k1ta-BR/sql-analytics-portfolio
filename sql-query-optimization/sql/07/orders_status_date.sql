SELECT COUNT(*)
FROM orders
WHERE status='paid'
  AND order_date >= '2024-04-01'
  AND order_date < '2024-07-01';
