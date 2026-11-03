import argparse
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Run SQL solutions and save CSV results.')
parser.add_argument('--task', type=int, choices=range(1, 8))
args = parser.parse_args()
db = ROOT / 'data/ecommerce.db'
if not db.exists():
    parser.error('Run python scripts/generate_data.py first.')
with sqlite3.connect(db) as conn:
    for query in sorted((ROOT / 'sql').glob('*.sql')):
        if args.task and int(query.name[:2]) != args.task:
            continue
        result = pd.read_sql_query(query.read_text(), conn)
        (ROOT / 'results').mkdir(exist_ok=True)
        result.to_csv(ROOT / 'results' / f'{query.stem}.csv', index=False)
        print(f'{query.name}: {len(result)} rows')
        print(result.head().to_string(index=False))
