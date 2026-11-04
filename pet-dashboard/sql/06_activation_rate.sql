WITH activation AS (
    SELECT u.user_id, u.signup_channel,
           EXISTS (
               SELECT 1 FROM orders o
               WHERE o.user_id = u.user_id AND o.status = 'paid'
                 AND o.order_date >= u.signup_date
                 AND o.order_date < DATE(u.signup_date, '+7 days')
           ) AS activated
    FROM users u
    WHERE :channel = 'all' OR u.signup_channel = :channel
)
SELECT signup_channel, COUNT(*) AS users, SUM(activated) AS activated_users,
       AVG(activated * 1.0) AS activation_rate
FROM activation
GROUP BY signup_channel
ORDER BY activation_rate DESC;
