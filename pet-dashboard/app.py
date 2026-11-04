"""Interactive portfolio dashboard for the first SQL project."""
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import analytics

st.set_page_config(page_title='Commerce Lab · SQL Analytics', page_icon='◈', layout='wide')
st.markdown('''<style>
[data-testid="stAppViewContainer"] { background: #f7f9fb; }
[data-testid="stSidebar"] { background: #edf2f5; border-right: 1px solid #dde5eb; }
.block-container { max-width: 1450px; padding-top: 2.4rem; padding-bottom: 2rem; }
h1, h2, h3 { color: #172d3b; letter-spacing: -0.025em; }
[data-testid="stMetric"] { background: white; border: 1px solid #dde5eb; border-radius: 12px; padding: 18px 20px; }
[data-testid="stMetricValue"] { color: #172d3b; font-size: clamp(1.2rem, 2vw, 1.9rem); }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; }
.eyebrow { color: #0b8678; font-size: 12px; letter-spacing: .14em; font-weight: 700; margin-bottom: 8px; }
.brand { font-size: 24px; font-weight: 750; color: #172d3b; letter-spacing: -.04em; }
.subtitle { color: #667985; font-size: 15px; margin: -5px 0 20px; }
</style>''', unsafe_allow_html=True)

TEAL = '#168b7c'
NAVY = '#203c50'
GOLD = '#d39738'
MUTED = '#a4bbc3'
SEGMENTS = ['no_paid_orders', 'one_order', '2_3_orders', '4_plus_orders']
SEGMENT_LABELS = {'no_paid_orders': 'Без покупок', 'one_order': '1 заказ',
                  '2_3_orders': '2–3 заказа', '4_plus_orders': '4+ заказа'}
CATEGORY_LABELS = {'electronics': 'Электроника', 'home': 'Дом', 'books': 'Книги',
                   'sport': 'Спорт', 'beauty': 'Красота', 'kids': 'Детские товары'}
CHANNEL_LABELS = {'all': 'Все каналы', 'organic': 'Органический трафик',
                  'paid_ads': 'Платная реклама', 'referral': 'Рекомендации', 'email': 'Email'}
COLUMN_LABELS = {
    'segment': 'Сегмент', 'users': 'Пользователи', 'avg_ltv': 'Средний LTV',
    'total_ltv': 'Суммарный LTV', 'month': 'Месяц', 'category': 'Категория',
    'product_id': 'ID товара', 'revenue': 'Выручка', 'rank_in_category': 'Место',
    'user_id': 'ID пользователя', 'promo_code': 'Промокод', 'paid_orders': 'Заказы',
    'avg_order_value': 'Средний чек', 'city': 'Город', 'buyers': 'Покупатели',
    'repeat_buyers': 'Повторные покупатели', 'repeat_rate': 'Повторные покупки, %',
    'overall_repeat_rate': 'Общая доля, %', 'signup_channel': 'Канал',
    'activated_users': 'Активированные', 'activation_rate': 'Активация, %',
    'order_id': 'ID заказа', 'order_date': 'Дата', 'order_revenue': 'Сумма заказа',
    'prev_avg_revenue': 'Предыдущее среднее', 'ratio': 'Превышение, раз',
}


@st.cache_data(show_spinner=False)
def get_metadata():
    return analytics.metadata()


@st.cache_data(show_spinner=False, max_entries=128)
def get_data(page, **params):
    return analytics.load_page(page, **params)


def number(value, decimals=0):
    return f'{value:,.{decimals}f}'.replace(',', ' ').replace('.', ',')


def chart(fig, key, height=340, percent=False):
    fig.update_layout(height=height, margin=dict(t=25, r=20, b=35, l=10),
                      paper_bgcolor='white', plot_bgcolor='white',
                      font=dict(family='Arial, sans-serif', size=13, color=NAVY),
                      showlegend=False, hoverlabel=dict(bgcolor='white'),
                      xaxis=dict(gridcolor='#edf2f5', zeroline=False),
                      yaxis=dict(gridcolor='#edf2f5', zeroline=False))
    if percent:
        fig.update_xaxes(tickformat='.0%')
    st.plotly_chart(fig, width='stretch', theme=None, key=key,
                    config={'displayModeBar': False})


def section(number_, title, description):
    st.markdown(f'<div class="eyebrow">{number_}</div>', unsafe_allow_html=True)
    st.subheader(title)
    st.caption(description)


def table_and_download(frame, key):
    display = frame.copy()
    for col in ('repeat_rate', 'overall_repeat_rate', 'activation_rate'):
        if col in display:
            display[col] = display[col] * 100
    for col in ('segment', 'category', 'signup_channel'):
        if col in display:
            labels = {'segment': SEGMENT_LABELS, 'category': CATEGORY_LABELS,
                      'signup_channel': CHANNEL_LABELS}[col]
            display[col] = display[col].map(labels).fillna(display[col])
    formats = {}
    for col in display:
        if pd.api.types.is_float_dtype(display[col]):
            formats[col] = st.column_config.NumberColumn(COLUMN_LABELS.get(col, col), format='%.2f')
        else:
            formats[col] = st.column_config.Column(COLUMN_LABELS.get(col, col))
    st.dataframe(display, hide_index=True, width='stretch', column_config=formats)
    st.download_button('Скачать CSV', frame.to_csv(index=False).encode('utf-8-sig'),
                       file_name=f'{key}.csv', mime='text/csv', key=f'download_{key}')


def query_details(names):
    with st.expander('SQL и правила расчёта'):
        st.write('Выручка = quantity × price; учитываются только оплаченные заказы. '
                 'Денежные показатели — в условных единицах. CSV сохраняет исходные '
                 'названия столбцов и доли от 0 до 1.')
        st.caption('Значения фильтров передаются в SQL параметрами, без подстановки в текст запроса.')
        for name in names:
            st.markdown(f'**{name}.sql**')
            st.code(analytics.sql_text(name), language='sql')


meta = get_metadata()
with st.sidebar:
    st.markdown('<div class="brand">◈ Commerce Lab</div>', unsafe_allow_html=True)
    st.caption('SQL ANALYTICS · PORTFOLIO')
    st.divider()
    page = st.radio('Раздел', ['Продажи', 'Пользователи', 'Возможности роста'], key='page')
    st.divider()
    channel = st.selectbox('Канал привлечения', ['all'] + meta['channels'],
                           format_func=lambda x: CHANNEL_LABELS.get(x, x), key='channel')
    st.caption('Канал фильтрует пользователей и связанные с ними покупки и события во всех разделах.')
    st.divider()
    st.markdown('**Учебные данные**')
    st.caption('700 пользователей · 80 товаров\n\n2 600 заказов · 9 499 событий\n\nСинтетический набор · seed 42')
    with st.expander('О проекте'):
        st.write('Семь SQL-задач по интернет-магазину: сегментация, ранжирование, '
                 'анализ промокодов, повторные покупки, активация и поиск аномалий.')

st.markdown('<div class="eyebrow">E-COMMERCE / SQL PORTFOLIO</div>', unsafe_allow_html=True)
st.title(page)
subtitles = {'Продажи': 'Выручка, лидеры категорий и промокоды за выбранный период.',
             'Пользователи': 'Ценность покупателей, повторные покупки и первые семь дней.',
             'Возможности роста': 'Интерес без покупки и заказы, которые выделяются в истории клиента.'}
st.markdown(f'<div class="subtitle">{subtitles[page]}</div>', unsafe_allow_html=True)

if page == 'Продажи':
    lo, hi = date.fromisoformat(meta['start']), date.fromisoformat(meta['end'])
    dates = st.date_input('Период заказов (обе даты включительно)', (lo, hi),
                          min_value=lo, max_value=hi, format='DD.MM.YYYY', key='sales_dates')
    if len(dates) != 2:
        st.info('Выбери конечную дату периода.')
        st.stop()
    params = dict(channel=channel, start=dates[0].isoformat(), end=dates[1].isoformat())
    data = get_data('sales', **params)
    kpi = data['00_sales'].iloc[0]
    for box, label, value in zip(st.columns(4),
            ['Выручка, у.е.', 'Оплаченные заказы', 'Покупатели', 'Средний чек, у.е.'],
            [number(kpi.revenue, 2), number(kpi.paid_orders), number(kpi.buyers), number(kpi.avg_order_value, 2)]):
        box.metric(label, value)
    st.write('')
    with st.container(border=True):
        section('ОБЗОР', 'Динамика выручки', 'По месяцам. Для неполного месяца учтена только часть внутри выбранного периода.')
        months = pd.period_range(dates[0], dates[1], freq='M').astype(str)
        monthly = data['00_monthly'].set_index('month').reindex(months, fill_value=0).rename_axis('month').reset_index()
        fig = go.Figure(go.Scatter(x=monthly.month, y=monthly.revenue, mode='lines+markers',
                                   fill='tozeroy', fillcolor='rgba(22,139,124,.10)',
                                   line=dict(color=TEAL, width=3), marker=dict(size=7),
                                   hovertemplate='%{x}<br>Выручка: %{y:,.2f} у.е.<extra></extra>'))
        fig.update_layout(yaxis_title='Выручка, у.е.', xaxis_title=None)
        chart(fig, 'monthly', height=300)
        with st.expander('Таблица по месяцам'):
            table_and_download(monthly, 'monthly_revenue')
    with st.container(border=True):
        section('ЗАДАЧА 02', 'Топ-3 товара в категории', 'Ранжирование по оплаченной выручке. При равенстве выше товар с меньшим ID.')
        top = data['02_top_products']
        if top.empty:
            st.info('За выбранный период нет оплаченных покупок.')
        else:
            c1, c2 = st.columns(2)
            month = c1.selectbox('Месяц', sorted(top.month.unique(), reverse=True), key='top_month')
            categories = sorted(top.loc[top.month.eq(month), 'category'].unique())
            category = c2.selectbox('Категория', categories, format_func=lambda x: CATEGORY_LABELS.get(x, x), key='top_category')
            selected = top[top.month.eq(month) & top.category.eq(category)].copy()
            fig = px.bar(selected, x='revenue', y=selected.product_id.map(lambda x: f'Товар #{x}'),
                         orientation='h', color_discrete_sequence=[TEAL], labels={'revenue':'Выручка, у.е.', 'y':''})
            fig.update_yaxes(autorange='reversed')
            chart(fig, 'top', height=250)
            table_and_download(selected, '02_top_products')
    with st.container(border=True):
        section('ЗАДАЧА 04', 'Промокоды', 'Только непустые промокоды с 20 и более оплаченными заказами в выбранном периоде и канале.')
        promos = data['04_promo_codes']
        if promos.empty:
            st.info('Нет промокодов, прошедших порог 20 заказов. Попробуй расширить период или выбрать все каналы.')
        else:
            fig = px.bar(promos, x='promo_code', y='revenue', color_discrete_sequence=[NAVY],
                         labels={'promo_code':'', 'revenue':'Выручка, у.е.'})
            chart(fig, 'promos', height=270)
            table_and_download(promos, '04_promo_codes')
    query_details(['00_sales', '00_monthly', '02_top_products', '04_promo_codes'])

elif page == 'Пользователи':
    st.caption('Весь доступный период · LTV и повторные покупки считаются по полной истории. Активация — дни 0–6 после регистрации.')
    data = get_data('users', channel=channel)
    segments = data['01_ltv_segments'].set_index('segment').reindex(SEGMENTS, fill_value=0).reset_index()
    repeat = data['05_repeat_rate']
    activation = data['06_activation_rate']
    total_users = int(segments.users.sum())
    activated = int(activation.activated_users.sum())
    overall = float(repeat.overall_repeat_rate.iloc[0]) if len(repeat) else 0
    avg_ltv = segments.total_ltv.sum() / total_users if total_users else 0
    for box, label, value in zip(st.columns(4),
            ['Пользователи', 'Средний LTV, у.е.', 'Повторные покупатели', 'Активация за 7 дней'],
            [number(total_users), number(avg_ltv, 2), f'{number(overall * 100, 1)}%', f'{number(activated / total_users * 100 if total_users else 0, 1)}%']):
        box.metric(label, value)
    st.write('')
    left, right = st.columns(2)
    with left, st.container(border=True):
        section('ЗАДАЧА 01', 'LTV-сегменты', 'Размер сегмента по числу оплаченных заказов. Пользователи без покупок включены.')
        fig = px.bar(segments, x='users', y=segments.segment.map(SEGMENT_LABELS), orientation='h',
                     color_discrete_sequence=[TEAL], text='users', labels={'users':'Пользователи', 'y':''})
        fig.update_yaxes(autorange='reversed')
        chart(fig, 'ltv')
        with st.expander('LTV по сегментам'):
            table_and_download(segments, '01_ltv_segments')
    with right, st.container(border=True):
        section('ЗАДАЧА 06', 'Активация по каналам', 'Хотя бы один оплаченный заказ в первые семь дней после регистрации.')
        fig = px.bar(activation, x='activation_rate', y=activation.signup_channel.map(CHANNEL_LABELS),
                     orientation='h', color_discrete_sequence=[NAVY],
                     text=activation.activation_rate.map(lambda x: f'{x:.1%}'),
                     labels={'activation_rate':'Доля активированных', 'y':''})
        fig.update_yaxes(autorange='reversed')
        fig.update_xaxes(range=[0, max(.2, float(activation.activation_rate.max()) * 1.25)])
        chart(fig, 'activation', percent=True)
        with st.expander('Пользователи и активация'):
            table_and_download(activation, '06_activation_rate')
    with st.container(border=True):
        section('ЗАДАЧА 05', 'Повторные покупки по городам', 'Доля покупателей с 2+ оплаченными заказами. Общая доля взвешена по покупателям выбранного канала.')
        if repeat.empty:
            st.info('В этом канале нет покупателей.')
        else:
            colors = [TEAL if r > overall else MUTED for r in repeat.repeat_rate]
            fig = go.Figure(go.Bar(x=repeat.repeat_rate, y=repeat.city, orientation='h', marker_color=colors,
                                   text=[f'{r:.1%}' for r in repeat.repeat_rate], textposition='outside',
                                   hovertemplate='%{y}<br>Повторные покупки: %{x:.1%}<extra></extra>'))
            fig.update_yaxes(autorange='reversed')
            fig.update_xaxes(range=[0, 1.08], title='Доля повторных покупателей')
            fig.add_vline(x=overall, line_dash='dot', line_color=GOLD)
            chart(fig, 'repeat', height=340, percent=True)
            st.caption(f'Пунктир: общая доля {overall:.2%}. Зелёным выделены города выше этой доли.')
            above_only = st.checkbox('В таблице только города выше общей доли', value=True, key='above_only')
            shown = repeat[repeat.repeat_rate > overall] if above_only else repeat
            table_and_download(shown, '05_repeat_rate')
    query_details(['01_ltv_segments', '05_repeat_rate', '06_activation_rate'])

else:
    st.caption('Весь доступный период · Сравнение просмотров и покупок по полной истории. Аномалии сравниваются только с предыдущими заказами.')
    data = get_data('insights', channel=channel)
    views = data['03_viewed_not_purchased']
    anomalies = data['07_anomalous_orders'].copy()
    for box, label, value in zip(st.columns(3),
            ['Пары «пользователь × категория»', 'Пользователи с интересом без покупки', 'Аномально крупные заказы'],
            [number(len(views)), number(views.user_id.nunique()), number(len(anomalies))]):
        box.metric(label, value)
    st.write('')
    with st.container(border=True):
        section('ЗАДАЧА 03', 'Смотрели, но не покупали', 'Пользователь смотрел товар категории, но не сделал ни одной оплаченной покупки в ней. Это не показатель конверсии.')
        if views.empty:
            st.info('Таких пар в выбранном канале нет.')
        else:
            counts = views.groupby('category').size().rename('users').reset_index().sort_values('users', ascending=False)
            fig = px.bar(counts, x='users', y=counts.category.map(CATEGORY_LABELS), orientation='h',
                         color_discrete_sequence=[TEAL], text='users', labels={'users':'Пользователи', 'y':''})
            fig.update_yaxes(autorange='reversed')
            chart(fig, 'unconverted')
            category = st.selectbox('Категория для таблицы', ['all'] + sorted(views.category.unique()),
                                   format_func=lambda x: 'Все категории' if x == 'all' else CATEGORY_LABELS.get(x, x), key='view_category')
            table_and_download(views if category == 'all' else views[views.category.eq(category)], '03_viewed_not_purchased')
    with st.container(border=True):
        section('ЗАДАЧА 07', 'Заказы выше обычного уровня', 'Сумма заказа строго больше трёх средних предыдущих оплаченных заказов клиента. Первый заказ исключён.')
        if anomalies.empty:
            st.info('Заказов, подходящих под это условие, нет.')
        else:
            anomalies['ratio'] = anomalies.order_revenue / anomalies.prev_avg_revenue
            fig = px.scatter(anomalies, x='prev_avg_revenue', y='order_revenue',
                             hover_data=['order_id', 'user_id', 'order_date'], color_discrete_sequence=[TEAL],
                             labels={'prev_avg_revenue':'Предыдущее среднее, у.е.', 'order_revenue':'Сумма заказа, у.е.'})
            max_x = float(anomalies.prev_avg_revenue.max()) * 1.05
            fig.add_trace(go.Scatter(x=[0, max_x], y=[0, max_x * 3], mode='lines',
                                    line=dict(color=GOLD, dash='dot'), hoverinfo='skip'))
            chart(fig, 'anomalies', height=360)
            st.caption('Пунктир — тройное предыдущее среднее. Это правило поиска необычных заказов, а не признак мошенничества.')
            table_and_download(anomalies, '07_anomalous_orders')
    query_details(['03_viewed_not_purchased', '07_anomalous_orders'])

st.divider()
st.caption('Commerce Lab · Учебный SQL-проект · Синтетические данные, seed 42 · Никита Латышев')
