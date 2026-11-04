WITH views AS (
    SELECT DISTINCT e.user_id, p.category
    FROM events e
    JOIN products p USING (product_id)
    JOIN users u USING (user_id)
    WHERE e.event_type = 'product_view'
      AND (:channel = 'all' OR u.signup_channel = :channel)
), purchases AS (
    SELECT DISTINCT o.user_id, p.category
    FROM orders o
    JOIN order_items oi USING (order_id)
    JOIN products p USING (product_id)
    WHERE o.status = 'paid'
)
SELECT v.user_id, v.category
FROM views v
WHERE (:category = 'all' OR v.category = :category)
  AND NOT EXISTS (
      SELECT 1 FROM purchases b
      WHERE b.user_id = v.user_id AND b.category = v.category
  )
ORDER BY v.category, v.user_id;
