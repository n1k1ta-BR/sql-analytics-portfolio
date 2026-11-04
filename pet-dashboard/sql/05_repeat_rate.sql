WITH buyers AS (
    SELECT u.user_id, u.city, COUNT(o.order_id) AS paid_orders
    FROM users u
    JOIN orders o USING (user_id)
    WHERE o.status = 'paid'
      AND (:channel = 'all' OR u.signup_channel = :channel)
    GROUP BY u.user_id, u.city
), overall AS (
    SELECT AVG(CASE WHEN paid_orders >= 2 THEN 1.0 ELSE 0.0 END) AS rate
    FROM buyers
)
SELECT city, COUNT(*) AS buyers,
       SUM(CASE WHEN paid_orders >= 2 THEN 1 ELSE 0 END) AS repeat_buyers,
       AVG(CASE WHEN paid_orders >= 2 THEN 1.0 ELSE 0.0 END) AS repeat_rate,
       (SELECT rate FROM overall) AS overall_repeat_rate
FROM buyers
GROUP BY city
ORDER BY repeat_rate DESC;
