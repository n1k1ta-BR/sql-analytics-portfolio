WITH per_order AS (
    SELECT o.order_id, o.promo_code, SUM(oi.quantity * oi.price) AS revenue
    FROM orders o
    JOIN users u USING (user_id)
    JOIN order_items oi USING (order_id)
    WHERE o.status = 'paid' AND o.promo_code IS NOT NULL
      AND o.order_date BETWEEN :start AND :end
      AND (:channel = 'all' OR u.signup_channel = :channel)
    GROUP BY o.order_id, o.promo_code
)
SELECT promo_code, COUNT(*) AS paid_orders, SUM(revenue) AS revenue,
       AVG(revenue) AS avg_order_value
FROM per_order
GROUP BY promo_code
HAVING COUNT(*) >= :min_orders
ORDER BY revenue DESC;
