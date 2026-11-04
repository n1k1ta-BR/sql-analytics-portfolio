WITH order_revenue AS (
    SELECT o.order_id, o.user_id, SUM(oi.quantity * oi.price) AS revenue
    FROM orders o
    JOIN users u USING (user_id)
    JOIN order_items oi USING (order_id)
    WHERE o.status = 'paid'
      AND o.order_date BETWEEN :start AND :end
      AND (:channel = 'all' OR u.signup_channel = :channel)
    GROUP BY o.order_id, o.user_id
)
SELECT COALESCE(SUM(revenue), 0) AS revenue,
       COUNT(*) AS paid_orders,
       COUNT(DISTINCT user_id) AS buyers,
       COALESCE(AVG(revenue), 0) AS avg_order_value
FROM order_revenue;
