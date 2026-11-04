WITH revenue AS (
    SELECT SUBSTR(o.order_date, 1, 7) AS month, p.category, p.product_id,
           SUM(oi.quantity * oi.price) AS revenue
    FROM orders o
    JOIN users u USING (user_id)
    JOIN order_items oi USING (order_id)
    JOIN products p USING (product_id)
    WHERE o.status = 'paid'
      AND o.order_date BETWEEN :start AND :end
      AND (:channel = 'all' OR u.signup_channel = :channel)
    GROUP BY month, p.category, p.product_id
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY month, category ORDER BY revenue DESC, product_id ASC
    ) AS rank_in_category
    FROM revenue
)
SELECT month, category, product_id, revenue, rank_in_category
FROM ranked
WHERE rank_in_category <= 3
  AND (:month = 'all' OR month = :month)
  AND (:category = 'all' OR category = :category)
ORDER BY month, category, rank_in_category;
