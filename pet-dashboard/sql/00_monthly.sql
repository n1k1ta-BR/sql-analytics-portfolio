SELECT SUBSTR(o.order_date, 1, 7) AS month,
       SUM(oi.quantity * oi.price) AS revenue,
       COUNT(DISTINCT o.order_id) AS paid_orders
FROM orders o
JOIN users u USING (user_id)
JOIN order_items oi USING (order_id)
WHERE o.status = 'paid'
  AND o.order_date BETWEEN :start AND :end
  AND (:channel = 'all' OR u.signup_channel = :channel)
GROUP BY month
ORDER BY month;
