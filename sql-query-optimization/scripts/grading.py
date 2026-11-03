#@title 🔒 Автопроверка оптимизаций — запустите один раз и не редактируйте
import re as _re
import time as _time
import sqlite3 as _sqlite3
import pandas as _pd
import numpy as _np

_BASELINES = {
1: """
SELECT COUNT(*) AS paid_orders
FROM orders
WHERE substr(order_date, 1, 7) = '2024-03'
  AND status = 'paid'
""",
2: """
SELECT user_id, COUNT(*) AS orders
FROM orders
WHERE status = 'paid'
  AND order_date >= '2024-04-01'
  AND order_date <  '2024-07-01'
GROUP BY user_id
HAVING COUNT(*) >= 3
""",
3: """
SELECT u.channel, SUM(oi.quantity * oi.price) AS revenue
FROM order_items oi
JOIN orders o USING(order_id)
JOIN users u USING(user_id)
WHERE o.status = 'paid'
  AND o.order_date >= '2024-01-01'
  AND o.order_date <  '2024-07-01'
GROUP BY u.channel
""",
4: """
SELECT u.user_id
FROM users u
WHERE NOT EXISTS (
  SELECT 1
  FROM events e
  WHERE e.user_id = u.user_id
    AND e.event_type = 'purchase'
)
""",
5: """
SELECT event_id, user_id, event_time, event_type
FROM events
WHERE user_id = 777
ORDER BY event_time DESC
LIMIT 50
""",
6: """
SELECT DISTINCT u.user_id, u.channel
FROM users u
JOIN orders o USING(user_id)
JOIN order_items oi USING(order_id)
WHERE o.status = 'paid'
  AND o.order_date >= '2024-05-01'
  AND o.order_date <  '2024-06-01'
"""
}

_REPRESENTATIVE = {
    'orders_status_date': """
SELECT COUNT(*)
FROM orders
WHERE status='paid'
  AND order_date >= '2024-04-01'
  AND order_date < '2024-07-01'
""",
    'latest_user_events': """
SELECT event_id,user_id,event_time,event_type
FROM events
WHERE user_id=777
ORDER BY event_time DESC
LIMIT 50
""",
    'events_type_date': """
SELECT COUNT(*)
FROM events
WHERE event_type='purchase'
  AND event_time >= '2024-04-01'
  AND event_time < '2024-07-01'
"""
}

def _strip_comments(s):
    s=_re.sub(r'/\*.*?\*/',' ',str(s),flags=_re.S)
    s=_re.sub(r'--[^\n]*',' ',s)
    return s.strip()

def _valid_query(sql):
    if not isinstance(sql,str) or not sql.strip(): return False,"Запрос не заполнен."
    s=_strip_comments(sql).rstrip(';').strip()
    if ';' in s: return False,"Нужен ровно один SELECT/WITH-запрос."
    if not _re.match(r'(?is)^(select|with)\b',s): return False,"Разрешены SELECT/WITH."
    if _re.search(r'\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace)\b',s,_re.I):
        return False,"Оптимизированный запрос не должен менять базу."
    return True,s

def _reset_indexes():
    rows=conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall()
    for (name,) in rows:
        safe=name.replace('"','""')
        conn.execute(f'DROP INDEX IF EXISTS "{safe}"')
    conn.commit()

def _apply_index_sql(index_sql):
    if index_sql is None: return []
    seq=[index_sql] if isinstance(index_sql,str) else list(index_sql)
    seq=[x for x in seq if isinstance(x,str) and x.strip()]
    names_before={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    for stmt in seq:
        s=_strip_comments(stmt).rstrip(';').strip()
        if ';' in s:
            raise ValueError("Каждый элемент должен содержать ровно один CREATE INDEX.")
        if not _re.match(r'(?is)^create\s+(unique\s+)?index\b',s):
            raise ValueError("В index_sql разрешены только CREATE INDEX.")
        conn.execute(s)
    conn.commit()
    names_after={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    return sorted(names_after-names_before)

def _indexes(table):
    out=[]
    for row in conn.execute(f"PRAGMA index_list('{table}')").fetchall():
        name=row[1]
        cols=[r[2] for r in conn.execute(f"PRAGMA index_info('{name}')").fetchall()]
        out.append((name,cols))
    return out

def _plan(sql):
    return _pd.read_sql_query('EXPLAIN QUERY PLAN '+sql,conn)

def _plan_text(sql):
    p=_plan(sql)
    return " | ".join(p['detail'].astype(str).tolist())

def _timing(sql, repeat=2):
    vals=[]
    for _ in range(repeat):
        t0=_time.perf_counter()
        _pd.read_sql_query(sql,conn)
        vals.append(_time.perf_counter()-t0)
    return min(vals)

def _task6_test_conn():
    # Небольшая детерминированная копия схемы: проверяем семантику без риска
    # подвесить Colab медленным correlated EXISTS без индекса.
    c=_sqlite3.connect(':memory:')
    u=_pd.read_sql_query("SELECT * FROM users WHERE user_id <= 1200",conn)
    o=_pd.read_sql_query("SELECT * FROM orders WHERE user_id <= 1200",conn)
    oi=_pd.read_sql_query("""
        SELECT oi.*
        FROM order_items oi
        JOIN orders o USING(order_id)
        WHERE o.user_id <= 1200
    """,conn)
    p=_pd.read_sql_query("SELECT * FROM products",conn)
    e=_pd.read_sql_query("SELECT * FROM events WHERE user_id <= 1200",conn)
    for name,df in [('users',u),('orders',o),('order_items',oi),('products',p),('events',e)]:
        df.to_sql(name,c,index=False,if_exists='replace')
    return c

def _same_result(a,b,ordered=False):
    if list(map(str.lower,a.columns.astype(str))) != list(map(str.lower,b.columns.astype(str))):
        return False
    if len(a)!=len(b): return False
    if not ordered:
        cols=list(a.columns)
        try:
            a=a.sort_values(cols,kind='stable').reset_index(drop=True)
            b=b.sort_values(cols,kind='stable').reset_index(drop=True)
        except Exception:
            a=a.astype(str).sort_values(cols,kind='stable').reset_index(drop=True)
            b=b.astype(str).sort_values(cols,kind='stable').reset_index(drop=True)
    else:
        a=a.reset_index(drop=True); b=b.reset_index(drop=True)
    for col in a.columns:
        if _pd.api.types.is_numeric_dtype(b[col]):
            aa=_pd.to_numeric(a[col],errors='coerce').to_numpy(dtype=float)
            bb=_pd.to_numeric(b[col],errors='coerce').to_numpy(dtype=float)
            if not _np.allclose(aa,bb,rtol=1e-5,atol=1e-4,equal_nan=True): return False
        else:
            if not (a[col].fillna('<NULL>').astype(str).to_numpy()==b[col].fillna('<NULL>').astype(str).to_numpy()).all():
                return False
    return True

def _has_index(table,predicate):
    return any(predicate(cols) for _,cols in _indexes(table))

def _explanation_ok(text, min_len=35):
    return isinstance(text,str) and len(text.strip())>=min_len

def _grade_status(score):
    if score>=99.5: return "✅ ПОЛНОЕ РЕШЕНИЕ"
    if score>=75: return "🟡 ХОРОШО, НО ЕСТЬ ЧТО ДОПРАВИТЬ"
    if score>=40: return "🟠 ЧАСТИЧНОЕ РЕШЕНИЕ"
    return "❌ РЕШЕНИЕ НЕ ПРОШЛО ПРОВЕРКУ"

def _show_plan(label,sql):
    print(f"\n{label}")
    display(_plan(sql))

def check_optimization(task_id, *, optimized_sql=None, index_sql=None, explanation=""):
    print("═"*78)
    print(f"Задача {task_id}")
    if task_id not in range(1,7):
        raise ValueError("Для задачи 7 используйте check_index_budget(...)")

    base=_BASELINES[task_id]
    _reset_indexes()
    # Исходный план строим всегда. Заведомо дорогие случаи не гоняем на полном наборе.
    base_plan=_plan(base)
    timing_note=""
    if task_id==4:
        base_result=_pd.read_sql_query("""
            SELECT u.user_id
            FROM users u
            WHERE u.user_id NOT IN (
                SELECT e.user_id FROM events e WHERE e.event_type='purchase'
            )
        """,conn)
        base_time=None
        timing_note="Исходный NOT EXISTS без индекса намеренно не исполнялся на полном наборе."
    elif task_id==6:
        base_result=None
        base_time=None
        timing_note="Семантика задачи 6 проверяется на уменьшенном наборе, чтобы медленный correlated EXISTS не подвешивал Colab."
    else:
        base_result=_pd.read_sql_query(base,conn)
        base_time=_timing(base,1)

    # В задачах 2/4/5 сам запрос может остаться исходным.
    if optimized_sql is None or (isinstance(optimized_sql,str) and not optimized_sql.strip()):
        if task_id in (2,4,5):
            optimized_sql=base
        else:
            print("📝 РЕШЕНИЕ ПОКА НЕ ЗАПОЛНЕНО")
            return {'score':0,'status':'not_submitted'}

    ok,q=_valid_query(optimized_sql)
    if not ok:
        print("⚠️",q)
        return {'score':0,'status':'invalid_sql'}

    try:
        created=_apply_index_sql(index_sql)
    except Exception as exc:
        print("⚠️ Ошибка в CREATE INDEX:",exc)
        return {'score':0,'status':'index_error'}

    try:
        plan=_plan(q)
        plan_text=" | ".join(plan['detail'].astype(str).tolist())
        if task_id==6:
            c6=_task6_test_conn()
            try:
                t0=_time.perf_counter()
                got=_pd.read_sql_query(q,c6)
                new_time=_time.perf_counter()-t0
                base_result=_pd.read_sql_query(base,c6)
            finally:
                c6.close()
        else:
            t0=_time.perf_counter()
            got=_pd.read_sql_query(q,conn)
            new_time=_time.perf_counter()-t0
    except Exception as exc:
        print("⚠️ Ошибка SQL:",exc)
        return {'score':0,'status':'sql_error'}

    same=_same_result(got,base_result,ordered=(task_id==5))
    score=0.0
    notes=[]

    if task_id==1:
        score += 45 if same else 0
        s=_strip_comments(q).lower()
        sargable=not _re.search(r'\b(substr|strftime|date)\s*\([^)]*order_date',s,_re.S)
        score += 20 if sargable else 0
        idx_ok=_has_index('orders',lambda c: 'order_date' in c and (c[0]=='order_date' or (c[0]=='status' and len(c)>1 and c[1]=='order_date')))
        uses_index=('SEARCH orders' in plan_text and 'INDEX' in plan_text)
        score += 15 if idx_ok else 0
        score += 15 if uses_index else 0
        score += 5 if _explanation_ok(explanation) else 0
        if not same: notes.append("Оптимизированный запрос меняет результат исходного.")
        if not sargable: notes.append("Фильтр по order_date всё ещё оборачивает колонку функцией.")
        if not idx_ok: notes.append("Не найден подходящий индекс, начинающийся с order_date либо (status, order_date).")
        if not uses_index: notes.append("В плане нет SEARCH orders ... USING INDEX.")

    elif task_id==2:
        score += 20 if same else 0
        idx_full=_has_index('orders',lambda c: len(c)>=3 and c[0]=='status' and 'order_date' in c[1:] and 'user_id' in c[1:])
        idx_partial=_has_index('orders',lambda c: len(c)>=2 and c[0]=='status' and 'order_date' in c[1:])
        score += 45 if idx_full else (28 if idx_partial else 0)
        uses=('SEARCH orders' in plan_text and 'INDEX' in plan_text)
        score += 25 if uses else 0
        score += 10 if _explanation_ok(explanation,50) else 0
        if not idx_full: notes.append("Для полного балла индекс должен начинаться с status и включать order_date и user_id.")
        if not uses: notes.append("План не показывает индексный SEARCH по orders.")

    elif task_id==3:
        score += 55 if same else 0
        s=_strip_comments(q).lower()
        preagg=bool(_re.search(r'order_items[\s\S]{0,700}group\s+by[\s\S]{0,120}order_id',s))
        score += 35 if preagg else 0
        score += 10 if _explanation_ok(explanation,45) else 0
        if not same: notes.append("Результат отличается от исходного запроса.")
        if not preagg: notes.append("Не обнаружена предварительная агрегация order_items до grain = order_id.")

    elif task_id==4:
        score += 35 if same else 0
        idx_ok=_has_index('events',lambda c: len(c)>=2 and set(c[:2])=={'user_id','event_type'})
        score += 30 if idx_ok else 0
        plan_ok=('SEARCH e' in plan_text and 'INDEX' in plan_text)
        score += 25 if plan_ok else 0
        score += 10 if _explanation_ok(explanation,40) else 0
        if not idx_ok: notes.append("Нужен составной индекс по user_id и event_type.")
        if not plan_ok: notes.append("Коррелированный подзапрос всё ещё не показывает индексный SEARCH по events.")

    elif task_id==5:
        score += 35 if same else 0
        idx_ok=_has_index('events',lambda c: len(c)>=2 and c[0]=='user_id' and c[1]=='event_time')
        score += 30 if idx_ok else 0
        search_ok=('SEARCH events' in plan_text and 'INDEX' in plan_text)
        no_sort=('USE TEMP B-TREE FOR ORDER BY' not in plan_text.upper())
        score += 15 if search_ok else 0
        score += 10 if no_sort else 0
        score += 10 if _explanation_ok(explanation,40) else 0
        if not idx_ok: notes.append("Нужен индекс, начинающийся с (user_id, event_time).")
        if not no_sort: notes.append("План всё ещё использует временную B-tree для ORDER BY.")

    elif task_id==6:
        score += 60 if same else 0
        s=_strip_comments(q).lower()
        no_distinct=not bool(_re.search(r'\bdistinct\b',s))
        score += 25 if no_distinct else 0
        no_temp_distinct=('USE TEMP B-TREE FOR DISTINCT' not in plan_text.upper())
        score += 10 if no_temp_distinct else 0
        score += 5 if _explanation_ok(explanation,35) else 0
        if not same: notes.append("Переписанный запрос возвращает другой набор пользователей.")
        if not no_distinct: notes.append("Финальный DISTINCT всё ещё присутствует.")
        if not no_temp_distinct: notes.append("План всё ещё строит временную B-tree для DISTINCT.")

    score=round(min(100,score),1)
    print(_grade_status(score),f"— {score:.1f}/100")
    print(f"Семантика результата: {'OK' if same else 'НЕ СОВПАДАЕТ'}")
    print("Созданные индексы:", created if created else "—")
    print("Индексы orders:", _indexes('orders') or "—")
    print("Индексы events:", _indexes('events') or "—")
    if timing_note:
        print("Время/режим проверки:",timing_note)
        print(f"Выполнение проверяемого запроса в режиме проверки: ~{new_time:.4f}s")
    else:
        print(f"Время (информативно, не основной критерий): до ~{base_time:.4f}s, после ~{new_time:.4f}s")
    if notes:
        print("\nЧто исправить:")
        for n in notes: print(" •",n)
    if not _explanation_ok(explanation,35):
        print(" • Добавьте короткое объяснение (минимум 1–2 содержательных предложения).")
    print("\nИсходный план:")
    display(base_plan)
    print("Новый план:")
    display(plan)
    return {'score':score,'status':_grade_status(score),'same_result':same,'plan':plan}

def check_index_budget(index_sqls, explanations=None):
    print("═"*78)
    print("Задача 7")
    _reset_indexes()
    seq=[x for x in (index_sqls or []) if isinstance(x,str) and x.strip()]
    if not seq:
        print("📝 РЕШЕНИЕ ПОКА НЕ ЗАПОЛНЕНО")
        return {'score':0,'status':'not_submitted'}
    if len(seq)>3:
        print("❌ Превышен бюджет: разрешено не больше 3 индексов.")
        return {'score':0,'status':'too_many_indexes'}
    try:
        created=_apply_index_sql(seq)
    except Exception as exc:
        print("⚠️ Ошибка CREATE INDEX:",exc)
        return {'score':0,'status':'index_error'}

    score=20
    details={}
    for name,q in _REPRESENTATIVE.items():
        p=_plan(q)
        text=" | ".join(p['detail'].astype(str).tolist())
        details[name]=(p,text)
        search=('SEARCH ' in text and 'INDEX' in text)
        score += 20 if search else 0

    latest_text=details['latest_user_events'][1].upper()
    no_temp='USE TEMP B-TREE FOR ORDER BY' not in latest_text
    score += 10 if no_temp else 0

    exps=explanations or []
    if isinstance(exps,str): exps=[exps]
    meaningful=sum(isinstance(x,str) and len(x.strip())>=30 for x in exps)
    if meaningful>=len(seq): score += 10

    score=round(min(100,score),1)
    print(_grade_status(score),f"— {score:.1f}/100")
    print(f"Индексный бюджет: {len(seq)}/3")
    print("Создано:",created)
    print("orders:",_indexes('orders') or "—")
    print("events:",_indexes('events') or "—")
    for name,(p,text) in details.items():
        print(f"\n{name}:")
        display(p)
    if not no_temp:
        print(" • Для запроса последних событий осталась временная сортировка.")
    if meaningful < len(seq):
        print(" • Для каждого индекса добавьте коротко: какой запрос ускоряет и каков компромисс (запись/размер).")
    return {'score':score,'status':_grade_status(score)}

print("Автопроверка оптимизаций готова ✅")
