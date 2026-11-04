"""Read parameterized SQL against the bundled snapshot of the first project."""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent
TABLES = ('users', 'products', 'orders', 'order_items', 'events')


def connect():
    conn = sqlite3.connect(':memory:')
    for table in TABLES:
        pd.read_csv(ROOT / 'data' / f'{table}.csv').to_sql(table, conn, index=False)
    return conn


def sql_text(name):
    return (ROOT / 'sql' / f'{name}.sql').read_text(encoding='utf-8')


def query(conn, name, **params):
    defaults = dict(channel='all', start='0001-01-01', end='9999-12-31',
                    month='all', category='all', min_orders=20)
    defaults.update(params)
    return pd.read_sql_query(sql_text(name), conn, params=defaults)


def metadata():
    with_conn = connect()
    try:
        dates = with_conn.execute('SELECT MIN(order_date), MAX(order_date) FROM orders').fetchone()
        channels = [r[0] for r in with_conn.execute('SELECT DISTINCT signup_channel FROM users ORDER BY 1')]
        categories = [r[0] for r in with_conn.execute('SELECT DISTINCT category FROM products ORDER BY 1')]
        return dict(start=dates[0], end=dates[1], channels=channels, categories=categories)
    finally:
        with_conn.close()


def load_page(page, **params):
    names = {
        'sales': ['00_sales', '00_monthly', '02_top_products', '04_promo_codes'],
        'users': ['01_ltv_segments', '05_repeat_rate', '06_activation_rate'],
        'insights': ['03_viewed_not_purchased', '07_anomalous_orders'],
    }[page]
    conn = connect()
    try:
        return {name: query(conn, name, **params) for name in names}
    finally:
        conn.close()
