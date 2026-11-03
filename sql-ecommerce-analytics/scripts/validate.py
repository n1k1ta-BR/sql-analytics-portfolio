import sqlite3
from pathlib import Path
import pandas as pd
from grading import _make_validation_conn, _expected, _exact_required, _GRADE_SPECS, _concept_score

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / 'data/ecommerce.db').exists():
    raise SystemExit('Run python scripts/generate_data.py first.')
connections = [('main', sqlite3.connect(ROOT / 'data/ecommerce.db'))]
connections += [(str(seed), _make_validation_conn(seed)) for seed in (31415, 27182)]
failed = []
try:
    for query in sorted((ROOT / 'sql').glob('*.sql')):
        task = int(query.name[:2])
        sql = query.read_text()
        for label, conn in connections:
            result = pd.read_sql_query(sql, conn)
            passed = _exact_required(result, _expected(task, conn), _GRADE_SPECS[task])
            passed = passed and _concept_score(task, sql)[0] == 10
            print(f'{query.name} / {label}: {"PASS" if passed else "FAIL"}')
            if not passed:
                failed.append((task, label))
finally:
    for _, conn in connections:
        conn.close()
if failed:
    raise SystemExit(f'Validation failed: {failed}')
print('All 21 checks passed.')
