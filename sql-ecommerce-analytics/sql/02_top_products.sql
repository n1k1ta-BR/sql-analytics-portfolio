with paid_orders AS(
  select order_id, oi.product_id, oi.quantity, oi.price, SUBSTR(o.order_date, 1, 7) as month, category
  FROM order_items oi JOIN orders o using(order_id) JOIN products p using(product_id)
  WHERE o.status = 'paid'
  ),

  category_ranged as (
    select product_id, month,  SUM(quantity * price) as prod_revenue, category from paid_orders
    GROUP BY product_id, month, category
  ),


  ranked as (select *, ROW_NUMBER() OVER(PARTITION BY month, category ORDER BY prod_revenue DESC, product_id ASC) as rank_in_category FROM category_ranged)

  select month, category, product_id, prod_revenue as revenue, rank_in_category FROM ranked
  WHERE rank_in_category BETWEEN 1 AND 3;
