"""Semantic checks for the SQL metrics and boundaries of the original tasks."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analytics


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.executescript('''
            CREATE TABLE users(user_id, signup_date, signup_channel, city);
            CREATE TABLE products(product_id, category);
            CREATE TABLE orders(order_id, user_id, order_date, status, promo_code);
            CREATE TABLE order_items(order_id, product_id, quantity, price);
            CREATE TABLE events(event_id, user_id, event_time, event_type, product_id);
            INSERT INTO users VALUES
                (1,'2024-01-01','organic','Москва'),
                (2,'2024-01-01','organic','Москва'),
                (3,'2024-01-01','email','Казань'),
                (4,'2024-01-01','email','Казань');
            INSERT INTO products VALUES (1,'books'),(2,'books'),(3,'home');
            INSERT INTO orders VALUES
                (1,1,'2024-01-01','paid','A'),
                (2,1,'2024-01-01','paid','A'),
                (3,1,'2024-01-03','paid','A'),
                (4,2,'2024-01-08','paid',NULL),
                (5,3,'2024-01-07','paid',NULL),
                (6,3,'2024-01-09','cancelled','A');
            INSERT INTO order_items VALUES
                (1,1,1,4.0),(1,1,1,6.0),
                (2,2,1,30.0),(3,3,1,70.0),
                (4,1,1,10.0),(5,2,1,10.0),(6,3,1,999.0);
            INSERT INTO events VALUES
                (1,3,'2024-01-02','product_view',3),
                (2,3,'2024-01-02','product_view',3),
                (3,3,'2024-01-02','product_view',2),
                (4,4,'2024-01-02','search',1);
        ''')

    def tearDown(self):
        self.conn.close()

    def q(self, name, **params):
        return analytics.query(self.conn, name, **params)

    def test_ltv_includes_zero_and_counts_orders_once(self):
        frame = self.q('01_ltv_segments').set_index('segment')
        self.assertEqual(frame.loc['no_paid_orders', 'users'], 1)
        self.assertEqual(frame.loc['no_paid_orders', 'total_ltv'], 0)
        self.assertEqual(frame.loc['2_3_orders', 'total_ltv'], 110)
        self.assertEqual(frame.users.sum(), 4)

    def test_activation_day_six_in_day_seven_out(self):
        frame = self.q('06_activation_rate').set_index('signup_channel')
        self.assertEqual(frame.loc['organic', 'activated_users'], 1)
        self.assertEqual(frame.loc['email', 'activated_users'], 1)
        self.assertEqual(frame.loc['email', 'users'], 2)

    def test_anomaly_strict_threshold_and_same_day_order(self):
        frame = self.q('07_anomalous_orders')
        self.assertEqual(frame.order_id.tolist(), [3])
        self.assertEqual(frame.iloc[0].prev_avg_revenue, 20)

    def test_views_ignore_cancelled_and_deduplicate(self):
        frame = self.q('03_viewed_not_purchased')
        self.assertEqual(list(frame.itertuples(index=False, name=None)), [(3, 'home')])

    def test_promo_average_is_per_order(self):
        frame = self.q('04_promo_codes', min_orders=3)
        self.assertEqual(frame.iloc[0].paid_orders, 3)
        self.assertAlmostEqual(frame.iloc[0].avg_order_value, 110 / 3)
        self.assertTrue(self.q('04_promo_codes', min_orders=4).empty)

    def test_repeat_denominator_excludes_non_buyers(self):
        frame = self.q('05_repeat_rate').set_index('city')
        self.assertEqual(frame.loc['Москва', 'repeat_rate'], .5)
        self.assertAlmostEqual(frame.loc['Казань', 'overall_repeat_rate'], 1 / 3)
        self.assertEqual(frame.loc['Казань', 'buyers'], 1)

    def test_filters_and_empty_period(self):
        frame = self.q('00_sales', channel='email', start='2024-01-07', end='2024-01-07')
        self.assertEqual(frame.iloc[0].revenue, 10)
        self.assertEqual(frame.iloc[0].paid_orders, 1)
        empty = self.q('00_sales', start='2023-01-01', end='2023-12-31').iloc[0]
        self.assertEqual(empty.revenue, 0)
        self.assertEqual(empty.avg_order_value, 0)
        self.assertTrue(self.q('00_sales', channel="' OR 1=1 --").iloc[0].paid_orders == 0)

    def test_top_ties_choose_smaller_id(self):
        self.conn.executescript('''
            DELETE FROM order_items; DELETE FROM orders; DELETE FROM products;
            INSERT INTO products VALUES (4,'books'),(3,'books'),(2,'books'),(1,'books');
            INSERT INTO orders VALUES (1,1,'2024-01-01','paid',NULL);
            INSERT INTO order_items VALUES (1,4,1,10.0),(1,3,1,10.0),(1,2,1,10.0),(1,1,1,10.0);
        ''')
        frame = self.q('02_top_products')
        self.assertEqual(frame.product_id.tolist(), [1, 2, 3])
        self.assertEqual(frame.rank_in_category.tolist(), [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
