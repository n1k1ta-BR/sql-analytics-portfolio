WITH per_order AS (
    SELECT o.order_id, o.user_id, o.order_date,
           SUM(oi.quantity * oi.price) AS order_revenue
    FROM orders o
    JOIN users u USING (user_id)
    JOIN order_items oi USING (order_id)
    WHERE o.status = 'paid'
      AND (:channel = 'all' OR u.signup_channel = :channel)
    GROUP BY o.order_id, o.user_id, o.order_date
), history AS (
    SELECT *, AVG(order_revenue) OVER (
        PARTITION BY user_id ORDER BY order_date, order_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS prev_avg_revenue
    FROM per_order
)
SELECT order_id, user_id, order_date, order_revenue, prev_avg_revenue
FROM history
WHERE order_revenue > 3 * prev_avg_revenue
ORDER BY order_date DESC, order_id DESC;
