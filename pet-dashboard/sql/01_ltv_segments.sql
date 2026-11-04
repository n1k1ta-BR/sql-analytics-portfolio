WITH per_user AS (
    SELECT u.user_id,
           COUNT(DISTINCT o.order_id) AS paid_orders,
           COALESCE(SUM(oi.quantity * oi.price), 0) AS ltv
    FROM users u
    LEFT JOIN orders o ON o.user_id = u.user_id AND o.status = 'paid'
    LEFT JOIN order_items oi USING (order_id)
    WHERE :channel = 'all' OR u.signup_channel = :channel
    GROUP BY u.user_id
), segments AS (
    SELECT *, CASE
        WHEN paid_orders = 0 THEN 'no_paid_orders'
        WHEN paid_orders = 1 THEN 'one_order'
        WHEN paid_orders BETWEEN 2 AND 3 THEN '2_3_orders'
        ELSE '4_plus_orders'
    END AS segment
    FROM per_user
)
SELECT segment, COUNT(*) AS users, AVG(ltv) AS avg_ltv, SUM(ltv) AS total_ltv
FROM segments
GROUP BY segment;
