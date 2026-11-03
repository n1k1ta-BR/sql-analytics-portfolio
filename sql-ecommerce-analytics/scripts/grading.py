#@title 🔒 Автопроверка — запустите один раз и не редактируйте
import re as _re
import sqlite3 as _sqlite3
import numpy as _np
import pandas as _pd

_GRADE_SPECS = {
    1: dict(
        required=['segment','users','avg_ltv','total_ltv'],
        keys=['segment'],
        values=['users','avg_ltv','total_ltv'],
        concept='',
    ),
    2: dict(
        required=['month','category','product_id','revenue','rank_in_category'],
        keys=['month','category','product_id'],
        values=['revenue','rank_in_category'],
        concept='window_rank',
    ),
    3: dict(
        required=['user_id','category'],
        keys=['user_id','category'],
        values=[],
        concept='',
    ),
    4: dict(
        required=['promo_code','paid_orders','revenue','avg_order_value'],
        keys=['promo_code'],
        values=['paid_orders','revenue','avg_order_value'],
        concept='',
    ),
    5: dict(
        required=['city','buyers','repeat_buyers','repeat_rate','overall_repeat_rate'],
        keys=['city'],
        values=['buyers','repeat_buyers','repeat_rate','overall_repeat_rate'],
        concept='',
    ),
    6: dict(
        required=['signup_channel','users','activated_users','activation_rate'],
        keys=['signup_channel'],
        values=['users','activated_users','activation_rate'],
        concept='',
    ),
    7: dict(
        required=['order_id','user_id','order_date','order_revenue','prev_avg_revenue'],
        keys=['order_id'],
        values=['user_id','order_date','order_revenue','prev_avg_revenue'],
        concept='window_avg',
    ),
}

def _strip_sql_comments(sql):
    sql = _re.sub(r'/\*.*?\*/', ' ', str(sql), flags=_re.S)
    sql = _re.sub(r'--[^\n]*', ' ', sql)
    return sql.strip()

def _validate_select(sql):
    if not isinstance(sql, str) or not sql.strip():
        return False, "Решение пока не заполнено."
    clean = _strip_sql_comments(sql).strip()
    clean = clean.rstrip(';').strip()
    if ';' in clean:
        return False, "В ячейке должен быть ровно один SELECT/WITH-запрос."
    if not _re.match(r'(?is)^(select|with)\b', clean):
        return False, "Разрешены только SELECT/WITH-запросы."
    forbidden = r'\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace)\b'
    if _re.search(forbidden, clean, flags=_re.I):
        return False, "Запрос изменяет базу. Для этой работы разрешены только читающие SELECT/WITH-запросы."
    return True, clean

def _read_tables(c):
    names = ['users','products','orders','order_items','events']
    return {n: _pd.read_sql_query(f'SELECT * FROM {n}', c) for n in names}

def _expected(task_id, c):
    t = _read_tables(c)
    u, p, o, oi, e = t['users'], t['products'], t['orders'], t['order_items'], t['events']
    oi = oi.copy()
    oi['item_revenue'] = oi['quantity'].astype(float) * oi['price'].astype(float)

    if task_id == 1:
        paid = o[o.status.eq('paid')][['order_id','user_id']].merge(
            oi[['order_id','item_revenue']], on='order_id', how='inner'
        )
        order_rev = paid.groupby(['order_id','user_id'], as_index=False)['item_revenue'].sum()
        per_user = order_rev.groupby('user_id').agg(
            paid_orders=('order_id','nunique'), ltv=('item_revenue','sum')
        ).reset_index()
        z = u[['user_id']].merge(per_user, on='user_id', how='left').fillna({'paid_orders':0,'ltv':0.0})
        z['paid_orders'] = z['paid_orders'].astype(int)
        z['segment'] = _np.select(
            [z.paid_orders.eq(0), z.paid_orders.eq(1), z.paid_orders.between(2,3), z.paid_orders.ge(4)],
            ['no_paid_orders','one_order','2_3_orders','4_plus_orders'],
            default='other'
        )
        out = z.groupby('segment', as_index=False).agg(
            users=('user_id','size'), avg_ltv=('ltv','mean'), total_ltv=('ltv','sum')
        )
        return out

    if task_id == 2:
        paid = o[o.status.eq('paid')][['order_id','order_date']].copy()
        paid['month'] = paid['order_date'].str.slice(0,7)
        z = paid.merge(oi[['order_id','product_id','item_revenue']], on='order_id').merge(
            p[['product_id','category']], on='product_id'
        )
        g = z.groupby(['month','category','product_id'], as_index=False)['item_revenue'].sum()
        g = g.rename(columns={'item_revenue':'revenue'})
        g = g.sort_values(['month','category','revenue','product_id'], ascending=[True,True,False,True])
        g['rank_in_category'] = g.groupby(['month','category']).cumcount() + 1
        return g[g.rank_in_category.le(3)][['month','category','product_id','revenue','rank_in_category']].reset_index(drop=True)

    if task_id == 3:
        views = e[e.event_type.eq('product_view')][['user_id','product_id']].merge(
            p[['product_id','category']], on='product_id'
        )[['user_id','category']].drop_duplicates()
        bought = o[o.status.eq('paid')][['order_id','user_id']].merge(
            oi[['order_id','product_id']], on='order_id'
        ).merge(p[['product_id','category']], on='product_id')[['user_id','category']].drop_duplicates()
        out = views.merge(bought.assign(_bought=1), on=['user_id','category'], how='left')
        return out[out._bought.isna()][['user_id','category']].drop_duplicates().reset_index(drop=True)

    if task_id == 4:
        paid = o[o.status.eq('paid') & o.promo_code.notna()][['order_id','promo_code']]
        z = paid.merge(oi[['order_id','item_revenue']], on='order_id')
        order_rev = z.groupby(['order_id','promo_code'], as_index=False)['item_revenue'].sum()
        out = order_rev.groupby('promo_code', as_index=False).agg(
            paid_orders=('order_id','nunique'),
            revenue=('item_revenue','sum'),
            avg_order_value=('item_revenue','mean')
        )
        return out[out.paid_orders.ge(20)].reset_index(drop=True)

    if task_id == 5:
        cnt = o[o.status.eq('paid')].groupby('user_id').size().rename('paid_orders').reset_index()
        buyers = cnt.merge(u[['user_id','city']], on='user_id', how='left')
        buyers['is_repeat'] = buyers.paid_orders.ge(2).astype(int)
        out = buyers.groupby('city', as_index=False).agg(
            buyers=('user_id','size'), repeat_buyers=('is_repeat','sum')
        )
        out['repeat_rate'] = out['repeat_buyers'] / out['buyers']
        overall = float(buyers['is_repeat'].mean()) if len(buyers) else _np.nan
        out['overall_repeat_rate'] = overall
        return out[out.repeat_rate.gt(overall)].reset_index(drop=True)

    if task_id == 6:
        paid = o[o.status.eq('paid')][['user_id','order_date']].copy()
        paid['order_date'] = _pd.to_datetime(paid['order_date'])
        z = u[['user_id','signup_date','signup_channel']].copy()
        z['signup_date'] = _pd.to_datetime(z['signup_date'])
        j = z.merge(paid, on='user_id', how='left')
        j['days_after_signup'] = (j['order_date'] - j['signup_date']).dt.days
        j['hit'] = j['days_after_signup'].between(0,6, inclusive='both').fillna(False)
        act = j.groupby('user_id', as_index=False)['hit'].max().rename(columns={'hit':'activated'})
        z = z.merge(act, on='user_id', how='left')
        z['activated'] = z['activated'].fillna(False).astype(int)
        out = z.groupby('signup_channel', as_index=False).agg(
            users=('user_id','size'), activated_users=('activated','sum')
        )
        out['activation_rate'] = out['activated_users'] / out['users']
        return out

    if task_id == 7:
        paid = o[o.status.eq('paid')][['order_id','user_id','order_date']].merge(
            oi[['order_id','item_revenue']], on='order_id'
        )
        g = paid.groupby(['order_id','user_id','order_date'], as_index=False)['item_revenue'].sum()
        g = g.rename(columns={'item_revenue':'order_revenue'})
        g = g.sort_values(['user_id','order_date','order_id']).reset_index(drop=True)
        g['prev_avg_revenue'] = g.groupby('user_id')['order_revenue'].transform(
            lambda s: s.expanding().mean().shift(1)
        )
        out = g[g['prev_avg_revenue'].notna() & (g.order_revenue > 3 * g.prev_avg_revenue)]
        return out[['order_id','user_id','order_date','order_revenue','prev_avg_revenue']].reset_index(drop=True)

    raise ValueError("Unknown task")

def _make_validation_conn(seed):
    rng = _np.random.default_rng(seed)
    c = _sqlite3.connect(':memory:')
    channels = _np.array(['organic','paid_ads','referral','email'])
    cities = _np.array(['Москва','Санкт-Петербург','Казань','Новосибирск','Екатеринбург'])
    categories = _np.array(['electronics','home','books','sport','beauty','kids'])
    brands = _np.array(['alpha','beta','gamma','delta','omega'])

    n_users, n_products, n_orders, n_events = 160, 40, 1200, 2800
    users2 = _pd.DataFrame({
        'user_id': _np.arange(1,n_users+1),
        'signup_date': _pd.to_datetime('2024-01-01') + _pd.to_timedelta(rng.integers(0,170,n_users), unit='D'),
        'signup_channel': rng.choice(channels,n_users),
        'city': rng.choice(cities,n_users),
    })
    users2['signup_date'] = users2['signup_date'].dt.strftime('%Y-%m-%d')
    products2 = _pd.DataFrame({
        'product_id': _np.arange(1,n_products+1),
        'category': rng.choice(categories,n_products),
        'brand': rng.choice(brands,n_products),
        'base_price': rng.integers(150,9000,n_products).astype(float),
    })
    order_users = rng.choice(users2.user_id,n_orders)
    signup_map = users2.set_index('user_id')['signup_date']
    offsets = rng.integers(0,190,n_orders)
    order_dates = _pd.to_datetime(signup_map.loc[order_users].to_numpy()) + _pd.to_timedelta(offsets,unit='D')
    orders2 = _pd.DataFrame({
        'order_id': _np.arange(1,n_orders+1),
        'user_id': order_users,
        'order_date': order_dates.strftime('%Y-%m-%d'),
        'status': rng.choice(['paid','cancelled','refunded'],n_orders,p=[.77,.16,.07]),
        'promo_code': rng.choice([None,'WELCOME10','SUMMER15','VIP20'],n_orders,p=[.63,.17,.13,.07]),
    })
    items=[]
    base_map=products2.set_index('product_id')['base_price'].to_dict()
    for oid in orders2.order_id:
        k=int(rng.integers(1,5))
        pids=rng.choice(products2.product_id,k,replace=False)
        for pid in pids:
            items.append((int(oid),int(pid),int(rng.choice([1,1,2,3])),round(float(base_map[int(pid)])*rng.uniform(.65,1.35),2)))
    items2=_pd.DataFrame(items,columns=['order_id','product_id','quantity','price'])

    # Гарантированно создаем хотя бы один "аномально крупный" поздний paid-заказ.
    paid_counts=orders2[orders2.status.eq('paid')].groupby('user_id').size()
    candidates=paid_counts[paid_counts.ge(2)].index
    if len(candidates):
        uid=int(candidates[0])
        oo=orders2[(orders2.user_id.eq(uid)) & orders2.status.eq('paid')].sort_values(['order_date','order_id'])
        target=int(oo.iloc[-1].order_id)
        items2.loc[items2.order_id.eq(target),'price'] *= 25

    events2=_pd.DataFrame({
        'event_id': _np.arange(1,n_events+1),
        'user_id': rng.choice(users2.user_id,n_events),
        'event_time': (_pd.to_datetime('2024-01-01') + _pd.to_timedelta(rng.integers(0,270,n_events),unit='D')).strftime('%Y-%m-%d'),
        'event_type': rng.choice(['app_open','product_view','add_to_cart','search'],n_events,p=[.43,.34,.11,.12]),
        'product_id': rng.choice(products2.product_id,n_events),
    })
    for name,df in [('users',users2),('products',products2),('orders',orders2),('order_items',items2),('events',events2)]:
        df.to_sql(name,c,index=False,if_exists='replace')
    return c

def _lower_columns(df):
    z=df.copy()
    z.columns=[str(x).strip().lower() for x in z.columns]
    return z

def _key_set(df, cols):
    if not cols:
        return set()
    def norm(v):
        if _pd.isna(v): return '<NULL>'
        if isinstance(v, (float, _np.floating)) and _np.isfinite(v):
            return f'{float(v):.8g}'
        return str(v)
    return {tuple(norm(v) for v in row) for row in df[cols].itertuples(index=False, name=None)}

def _value_accuracy(got, exp, keys, vals):
    if not vals:
        return 1.0
    if not keys:
        return 0.0
    g=got[keys+vals].drop_duplicates(subset=keys, keep='first')
    e=exp[keys+vals].drop_duplicates(subset=keys, keep='first')
    m=e.merge(g,on=keys,how='left',suffixes=('_exp','_got'),indicator=True)
    scores=[]
    for col in vals:
        a=m[f'{col}_exp']
        b=m[f'{col}_got']
        if _pd.api.types.is_numeric_dtype(a):
            aa=_pd.to_numeric(a,errors='coerce').to_numpy(dtype=float)
            bb=_pd.to_numeric(b,errors='coerce').to_numpy(dtype=float)
            ok=_np.isclose(aa,bb,rtol=1e-5,atol=1e-4,equal_nan=True)
        else:
            ok=(a.fillna('<NULL>').astype(str).to_numpy()==b.fillna('<NULL>').astype(str).to_numpy())
        ok = ok & m['_merge'].eq('both').to_numpy()
        scores.append(float(ok.mean()) if len(ok) else 1.0)
    return float(_np.mean(scores)) if scores else 1.0

def _concept_score(task_id, sql):
    s=_strip_sql_comments(sql).lower()
    if task_id==2:
        has_over=bool(_re.search(r'\bover\s*\(',s))
        has_rank=bool(_re.search(r'\b(row_number|rank|dense_rank)\s*\(',s))
        return (10 if has_over and has_rank else 0,
                "" if has_over and has_rank else "По условию нужна оконная функция ранжирования (`ROW_NUMBER`/`RANK`/`DENSE_RANK`).")
    if task_id==7:
        has_avg=bool(_re.search(r'\bavg\s*\([^)]*\)\s*over\s*\(',s,_re.S))
        return (10 if has_avg else 0,
                "" if has_avg else "По условию среднее предыдущих заказов нужно посчитать оконной функцией `AVG(...) OVER (...)`.")
    return 10, ""

def _exact_required(got, exp, spec):
    got=_lower_columns(got); exp=_lower_columns(exp)
    req=spec['required']
    if any(c not in got.columns for c in req): return False
    got=got[req].copy(); exp=exp[req].copy()
    keys=spec['keys']; vals=spec['values']
    if len(got)!=len(exp): return False
    if len(_key_set(got,keys)) != len(got): return False
    if _key_set(got,keys) != _key_set(exp,keys): return False
    return _value_accuracy(got,exp,keys,vals) >= 0.999999

def _status(score):
    if score >= 99.5: return "✅ ПОЛНОЕ РЕШЕНИЕ"
    if score >= 80: return "🟡 ПОЧТИ ГОТОВО"
    if score >= 45: return "🟠 ЧАСТИЧНОЕ РЕШЕНИЕ"
    return "❌ НЕВЕРНОЕ РЕШЕНИЕ"

def check_sql(task_id, sql, *, show_preview=True):
    ok, clean = _validate_select(sql)
    print("─"*72)
    print(f"Задача {task_id}")
    if not ok:
        if clean == "Решение пока не заполнено.":
            print("📝 РЕШЕНИЕ ПОКА НЕ ЗАПОЛНЕНО")
        else:
            print("⚠️ SQL НЕ ПРИНЯТ")
            print(clean)
        return {'score':0,'status':'not_submitted'}

    spec=_GRADE_SPECS[task_id]
    try:
        got=_pd.read_sql_query(clean,conn)
    except Exception as exc:
        print("⚠️ ОШИБКА SQL")
        print(f"{type(exc).__name__}: {exc}")
        return {'score':0,'status':'sql_error'}

    exp=_expected(task_id,conn)
    g=_lower_columns(got); e=_lower_columns(exp)
    req=spec['required']
    present=[c for c in req if c in g.columns]
    missing=[c for c in req if c not in g.columns]
    schema_ratio=len(present)/len(req)
    schema_points=15*schema_ratio

    if missing:
        concept_points,concept_msg=_concept_score(task_id,clean)
        score=round(schema_points + concept_points,1)
        print(_status(score),f"— {score:.1f}/100")
        print("Не хватает обязательных столбцов:", ", ".join(missing))
        print("Ожидаются:", ", ".join(req))
        if concept_msg: print("Требование метода:",concept_msg)
        if show_preview and len(got):
            print("\nВаш результат (первые 5 строк):")
            display(got.head())
        return {'score':score,'status':_status(score),'missing_columns':missing}

    g2=g[req].copy(); e2=e[req].copy()
    keys=spec['keys']; vals=spec['values']
    gs=_key_set(g2,keys); es=_key_set(e2,keys)
    inter=len(gs & es)
    precision=inter/len(gs) if gs else (1.0 if not es else 0.0)
    recall=inter/len(es) if es else (1.0 if not gs else 0.0)
    key_f1=(2*precision*recall/(precision+recall)) if (precision+recall) else 0.0
    duplicate_penalty = 1.0 if len(gs)==len(g2) else max(0.5, len(gs)/max(len(g2),1))
    value_acc=_value_accuracy(g2,e2,keys,vals)
    concept_points,concept_msg=_concept_score(task_id,clean)

    score = 15 + 35*key_f1*duplicate_penalty + 40*value_acc*key_f1 + concept_points

    # Дополнительные датасеты запускаем только для уже почти правильных решений.
    robustness_passed=0
    robustness_total=0
    if score >= 90:
        for seed in (31415,27182):
            c2=_make_validation_conn(seed)
            try:
                gtest=_pd.read_sql_query(clean,c2)
                etest=_expected(task_id,c2)
                passed=_exact_required(gtest,etest,spec)
            except Exception:
                passed=False
            finally:
                c2.close()
            robustness_total += 1
            robustness_passed += int(passed)
        if robustness_passed < robustness_total:
            score=min(score, 85 if robustness_passed==1 else 75)

    score=round(min(100,max(0,score)),1)
    exact_main=_exact_required(g2,e2,spec)
    status=_status(score)
    print(status,f"— {score:.1f}/100")
    print(f"Схема: {'OK' if not missing else 'есть проблемы'} | "
          f"ключи/строки: precision={precision:.2%}, recall={recall:.2%} | "
          f"значения: {value_acc:.2%}")
    if len(gs)!=len(g2):
        print("Есть дубликаты по ключевым столбцам — проверьте зерно результата.")
    if concept_msg:
        print("Требование метода:",concept_msg)
    if robustness_total:
        print(f"Дополнительные тесты на других данных: {robustness_passed}/{robustness_total}")
        if robustness_passed < robustness_total:
            print("Результат похож на правильный на основном наборе, но решение не обобщается на новые данные.")
    if not exact_main and not missing:
        missing_keys=list(es-gs)[:3]
        extra_keys=list(gs-es)[:3]
        if missing_keys: print("Примеры пропущенных ключей:",missing_keys)
        if extra_keys: print("Примеры лишних ключей:",extra_keys)
    if show_preview:
        print("\nВаш результат (первые 5 строк):")
        display(got.head())
    return {'score':score,'status':status,'robustness':(robustness_passed,robustness_total)}

print("Автопроверка готова ✅")
