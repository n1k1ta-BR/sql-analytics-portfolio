"""Reproduce the synthetic data from the original SQL project (seed=42)."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
(ROOT / 'data').mkdir(exist_ok=True)
import sqlite3
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
conn = sqlite3.connect(':memory:')

channels = np.array(['organic', 'paid_ads', 'referral', 'email'])
cities = np.array(['Москва', 'Санкт-Петербург', 'Казань', 'Новосибирск', 'Екатеринбург'])
categories = np.array(['electronics', 'home', 'books', 'sport', 'beauty', 'kids'])
brands = np.array(['alpha', 'beta', 'gamma', 'delta', 'omega'])

n_users = 700
users = pd.DataFrame({
    'user_id': np.arange(1, n_users + 1),
    'signup_date': pd.to_datetime('2024-01-01') + pd.to_timedelta(rng.integers(0, 190, n_users), unit='D'),
    'signup_channel': rng.choice(channels, n_users, p=[0.38, 0.32, 0.18, 0.12]),
    'city': rng.choice(cities, n_users),
})
users['signup_date'] = users['signup_date'].dt.strftime('%Y-%m-%d')

n_products = 80
base_price = rng.integers(250, 7000, n_products)
products = pd.DataFrame({
    'product_id': np.arange(1, n_products + 1),
    'category': rng.choice(categories, n_products),
    'brand': rng.choice(brands, n_products),
    'base_price': base_price.astype(float),
})

n_orders = 2600
order_users = rng.choice(users['user_id'], n_orders)
user_signup = users.set_index('user_id').loc[order_users, 'signup_date'].to_numpy()
order_dates = pd.to_datetime(user_signup) + pd.to_timedelta(rng.integers(0, 190, n_orders), unit='D')
statuses = rng.choice(['paid', 'cancelled', 'refunded'], n_orders, p=[0.78, 0.16, 0.06])
promos = rng.choice([None, 'WELCOME10', 'SUMMER15', 'VIP20'], n_orders, p=[0.68, 0.16, 0.11, 0.05])
orders = pd.DataFrame({
    'order_id': np.arange(1, n_orders + 1),
    'user_id': order_users,
    'order_date': order_dates.strftime('%Y-%m-%d'),
    'status': statuses,
    'promo_code': promos,
})

items = []
for oid in orders['order_id']:
    k = rng.integers(1, 5)
    pids = rng.choice(products['product_id'], k, replace=False)
    for pid in pids:
        base = float(products.loc[products.product_id == pid, 'base_price'].iloc[0])
        price = round(base * rng.uniform(0.75, 1.25), 2)
        qty = int(rng.choice([1, 1, 1, 2, 3]))
        items.append((oid, int(pid), qty, price))
order_items = pd.DataFrame(items, columns=['order_id', 'product_id', 'quantity', 'price'])

# Events for homework-style behavioral tasks
events = pd.DataFrame({
    'event_id': np.arange(1, 9500),
    'user_id': rng.choice(users['user_id'], 9499),
    'event_time': (pd.to_datetime('2024-01-01') + pd.to_timedelta(rng.integers(0, 280, 9499), unit='D')).strftime('%Y-%m-%d'),
    'event_type': rng.choice(['app_open', 'product_view', 'add_to_cart', 'search'], 9499, p=[0.45, 0.32, 0.11, 0.12]),
    'product_id': rng.choice(products['product_id'], 9499),
})

for name, df in [('users', users), ('products', products), ('orders', orders), ('order_items', order_items), ('events', events)]:
    df.to_sql(name, conn, index=False, if_exists='replace')


for name, df in [('users', users), ('products', products), ('orders', orders), ('order_items', order_items), ('events', events)]:
    df.to_csv(ROOT / 'data' / f'{name}.csv', index=False)
conn.close()
print('Five CSV files exported to dashboard/data/.')
