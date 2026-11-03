import contextlib
import io
import json
import platform
import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
import grading

ROOT = Path(__file__).resolve().parents[1]
db = ROOT / 'data/ecommerce.db'
if not db.exists():
    raise SystemExit('Run python scripts/generate_data.py first.')
output = ROOT / 'results'
output.mkdir(exist_ok=True)
config = json.loads((ROOT / 'docs/explanations.json').read_text())
summary = []
logs = io.StringIO()

def show_plan(frame):
    print(frame.to_string(index=False))

def read_sql(folder, name):
    file = folder / name
    return file.read_text().strip().rstrip(';') if file.exists() else None

def read_indexes(folder):
    text = read_sql(folder, 'indexes.sql')
    return [s.strip() for s in text.split(';') if s.strip()] if text else []

# Source grading functions share this connection and reset indexes per task.
grading.conn = sqlite3.connect(db, cached_statements=0)
grading.conn.execute('PRAGMA cache_size = -200000')
grading.conn.execute('PRAGMA temp_store = MEMORY')
grading.display = show_plan
try:
    for spec in config:
        task = spec['task']
        folder = ROOT / 'sql' / f'{task:02d}'
        grading._reset_indexes()
        base = read_sql(folder, 'baseline.sql')
        if base:
            grading._plan(base).to_csv(output / f'{task:02d}_plan_before.csv', index=False)
        with contextlib.redirect_stdout(logs):
            if task < 7:
                result = grading.check_optimization(
                    task, optimized_sql=read_sql(folder, 'optimized.sql'),
                    index_sql=read_indexes(folder), explanation=spec['explanation'])
            else:
                result = grading.check_index_budget(read_indexes(folder), spec['explanations'])
        if task < 7:
            result['plan'].to_csv(output / f'{task:02d}_plan_after.csv', index=False)
        else:
            for file in sorted(folder.glob('*.sql')):
                if file.name != 'indexes.sql':
                    grading._plan(file.read_text()).to_csv(output / f'07_{file.stem}_plan.csv', index=False)
        summary.append({'task':task, 'score':result['score'],
                        'same_result':result.get('same_result'), 'status':result['status']})
        print(f'Task {task}: {result["score"]}/100')
finally:
    grading._reset_indexes()
    grading.conn.close()
(output / 'comparison.txt').write_text(logs.getvalue())
pd.DataFrame(summary).to_csv(output / 'summary.csv', index=False)
(output / 'environment.json').write_text(json.dumps({
    'python':platform.python_version(), 'sqlite':sqlite3.sqlite_version,
    'numpy':np.__version__, 'pandas':pd.__version__, 'seed':7,
    'timing_note':'Tasks 4 and 6 use the special validation modes of the source notebook. Timings are illustrative, not a production benchmark.'
},indent=2))
if any(row['score'] != 100 for row in summary):
    raise SystemExit('Some checks failed; see results/comparison.txt')
print('All 7 tasks passed. Plans and comparison saved to results/.')
