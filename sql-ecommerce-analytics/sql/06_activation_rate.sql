WITH paid_orders AS (
  select user_id, signup_date, signup_channel, order_id, order_date, status FROM orders o JOIN users u using(user_id)
),

duration AS (
  select user_id, julianday(order_date) - julianday(signup_date) AS reg_to_bought, signup_channel
  FROM paid_orders
  WHERE status = 'paid'
),

activated_users as (
  select signup_channel, COUNT(DISTINCT user_id) AS activated_users FROM duration
  WHERE reg_to_bought >= 0 AND reg_to_bought < 7
  GROUP BY signup_channel
),



total_channel_users AS (
  select signup_channel, COUNT(DISTINCT user_id) as total_channel_users from users
  GROUP BY signup_channel
),

result AS (
  select signup_channel, total_channel_users as users,COALESCE(activated_users, 0) AS activated_users, COALESCE(activated_users, 0) * 1.0 / total_channel_users AS activation_rate FROM total_channel_users tcu LEFT JOIN activated_users au using(signup_channel)
)

select * from result;
