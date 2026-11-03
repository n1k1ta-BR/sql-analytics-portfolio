WITH order_user_category AS (
select order_id, user_id, category FROM orders o JOIN order_items oi using(order_id) JOIN products pr using(product_id)
WHERE o.status = 'paid' ),

user_prod_validevent AS(
select DISTINCT user_id, category FROM events e JOIN products pr using(product_id)
WHERE event_type = 'product_view')

select * from user_prod_validevent upv
WHERE NOT EXISTS(
  SELECT 1
  FROM order_user_category ouc
  WHERE ouc.user_id = upv.user_id
  AND ouc.category = upv.category
);
