SELECT COUNT(*) AS paid_orders
FROM orders
WHERE substr(order_date, 1, 7) = '2024-03'
  AND status = 'paid';
