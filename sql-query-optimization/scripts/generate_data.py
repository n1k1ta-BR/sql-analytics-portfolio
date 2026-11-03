from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
(ROOT / "data").mkdir(exist_ok=True)
db_path = ROOT / "data/ecommerce.db"
import sqlite3
import time
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
conn = sqlite3.connect(db_path)
conn.execute('PRAGMA cache_size = -200000')
conn.execute('PRAGMA temp_store = MEMORY')

channels = np.array(['organic', 'paid_ads', 'referral', 'email', 'partner'])
cities = np.array(['Москва', 'Санкт-Петербург', 'Казань', 'Новосибирск', 'Екатеринбург'])

n_users = 12000
users = pd.DataFrame({
    'user_id': np.arange(1, n_users + 1),
    'signup_date': (pd.to_datetime('2023-01-01') + pd.to_timedelta(rng.integers(0, 640, n_users), unit='D')).strftime('%Y-%m-%d'),
    'channel': rng.choice(channels, n_users, p=[0.34, 0.30, 0.16, 0.12, 0.08]),
    'city': rng.choice(cities, n_users),
    'email': [f'user{i}@example.com' for i in range(1, n_users + 1)],
})

n_products = 400
products = pd.DataFrame({
    'product_id': np.arange(1, n_products + 1),
    'category': rng.choice(['electronics','home','books','sport','beauty','kids','food'], n_products),
    'base_price': rng.integers(200, 12000, n_products).astype(float),
})
base_by_product = products.set_index('product_id')['base_price'].to_dict()

n_orders = 65000
orders = pd.DataFrame({
    'order_id': np.arange(1, n_orders + 1),
    'user_id': rng.choice(users['user_id'], n_orders),
    'order_date': (pd.to_datetime('2023-01-01') + pd.to_timedelta(rng.integers(0, 640, n_orders), unit='D')).strftime('%Y-%m-%d'),
    'status': rng.choice(['paid','cancelled','refunded'], n_orders, p=[0.74,0.20,0.06]),
})

item_counts = rng.integers(1, 5, n_orders)
order_ids = np.repeat(orders['order_id'].to_numpy(), item_counts)
product_ids = rng.choice(products['product_id'].to_numpy(), len(order_ids), replace=True)
base_prices = np.array([base_by_product[int(pid)] for pid in product_ids])
order_items = pd.DataFrame({
    'order_id': order_ids,
    'product_id': product_ids,
    'quantity': rng.choice([1, 1, 2, 3], len(order_ids)),
    'price': np.round(base_prices * rng.uniform(0.7, 1.25, len(order_ids)), 2),
})

n_events = 180000
events = pd.DataFrame({
    'event_id': np.arange(1, n_events + 1),
    'user_id': rng.choice(users['user_id'], n_events),
    'event_time': (pd.to_datetime('2023-01-01') + pd.to_timedelta(rng.integers(0, 640, n_events), unit='D')).strftime('%Y-%m-%d'),
    'event_type': rng.choice(['app_open','product_view','add_to_cart','checkout_start','purchase'], n_events, p=[.42,.32,.12,.09,.05]),
    'product_id': rng.choice(products['product_id'], n_events),
})

for name, df in [('users', users), ('products', products), ('orders', orders), ('order_items', order_items), ('events', events)]:
    df.to_sql(name, conn, index=False, if_exists='replace')


conn.close()
print(f"Database created: {db_path}")
