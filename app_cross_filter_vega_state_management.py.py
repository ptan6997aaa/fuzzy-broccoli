import dash
from dash import dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_vega_components as dvc # 核心组件库
import altair as alt
import pandas as pd
import os

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. DATA LOADING & PREPROCESSING (与原版保持一致)                              │
# └──────────────────────────────────────────────────────────────────────────────┘
def load_data():
    try:
        # 这里假设你本地有文件，为了演示方便，如果文件不存在，我生成一些模拟数据
        if os.path.exists("Details.csv") and os.path.exists("Orders.csv"):
            df_d = pd.read_csv("Details.csv")
            df_o = pd.read_csv("Orders.csv")
            df_merged = pd.merge(df_d, df_o, on="Order ID", how="inner")
        else:
            raise FileNotFoundError("Files not found")
    except Exception as e:
        print(f"Loading Mock Data: {e}")

    # 数据清洗
    # 统一字符串格式，比如防止 'Chairs ' 和 'Chairs' 不匹配
    str_cols = ["Sub-Category", "State", "CustomerName"]
    for col in str_cols:
        if col in df_merged.columns:
            df_merged[col] = df_merged[col].astype(str).str.strip()
            
    return df_merged

df = load_data()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. UI LAYOUT (替换 dcc.Graph 为 dvc.Vega)                                     │
# └──────────────────────────────────────────────────────────────────────────────┘
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

KPI_STYLE = {
    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    "color": "white",
    "box-shadow": "0 4px 6px rgba(0,0,0,0.1)",
    "border": "none",
    "border-radius": "10px"
}

CHART_CARD_STYLE = {
    "box-shadow": "0 2px 4px rgba(0,0,0,0.05)",
    "border": "none",
    "border-radius": "8px",
    "overflow": "hidden" # 防止 Vega 图表溢出
}

app.layout = dbc.Container([
    # ── State Storage ──
    # 使用 Store 可以在多个回调之间保持状态，实现多条件组合筛选
    # store-subcat: 存储 Sub-Category 的筛选值 (默认 'All')
    dcc.Store(id='store-subcat', data='All'),
    # store-state: 存储 State 的筛选值 (默认 'All')
    dcc.Store(id='store-state', data='All'),
    # store-state: 存储 Customer 的筛选值 (默认 'All')
    dcc.Store(id='store-customer', data='All'),

    # ── Header ──
    dbc.Row([
        dbc.Col(html.H2("📊 Product Sales Report", className="fw-bold my-3"), width=9),
        dbc.Col(
            dbc.Button("↺ Reset All Filters", id="btn-reset", color="danger", outline=True, className="mt-4 w-100 shadow-sm"),
            width=3
        )
    ], className="mb-4 border-bottom pb-3"),

    # ── Row 1: KPI Cards (保持不变) ──
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Sales"), html.H3(id="kpi-amount", className="fw-bold")]), style=KPI_STYLE), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Profit"), html.H3(id="kpi-profit", className="fw-bold")]), style=KPI_STYLE), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Quantity Sold"), html.H3(id="kpi-quantity", className="fw-bold")]), style=KPI_STYLE), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Orders"), html.H3(id="kpi-orders", className="fw-bold")]), style=KPI_STYLE), width=3),
    ], className="mb-4"),

    # ── Row 2: Charts (使用 dvc.Vega) ──
    # 注意：我们需要定义 signalsToObserve，这告诉 Dash 要监听 Vega 图表内部的哪个参数变化
    dbc.Row([
        # Chart 1
        dbc.Col(dbc.Card([
            dbc.CardHeader("Profit by Sub-Category", className="bg-white fw-bold border-0"),
            dbc.CardBody(dvc.Vega(id="chart-subcat", signalsToObserve=["sel_subcat"], style={'width': '100%', 'height': '300px'}))
        ], style=CHART_CARD_STYLE), width=4),

        # Chart 2
        dbc.Col(dbc.Card([
            dbc.CardHeader("Sales by State", className="bg-white fw-bold border-0"),
            dbc.CardBody(dvc.Vega(id="chart-state", signalsToObserve=["sel_state"], style={'width': '100%', 'height': '300px'}))
        ], style=CHART_CARD_STYLE), width=4),

        # Chart 3
        dbc.Col(dbc.Card([
            dbc.CardHeader("Top Customers", className="bg-white fw-bold border-0"),
            dbc.CardBody(dvc.Vega(id="chart-customer", signalsToObserve=["sel_cust"], style={'width': '100%', 'height': '300px'}))
        ], style=CHART_CARD_STYLE), width=4),
    ]),
    
    dbc.Row(dbc.Col(html.Div(id="filter-status", className="text-muted small mt-4 text-end fst-italic")))

], fluid=True, className="bg-light vh-100 p-4")


# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. LOGIC PART A: FILTER STATE MANAGEMENT (交互逻辑核心)                       │
# └──────────────────────────────────────────────────────────────────────────────┘
@app.callback(
    [Output('store-subcat', 'data'), 
     Output('store-state', 'data'),
     Output('store-customer', 'data')],
    [Input('btn-reset', 'n_clicks'),
     Input('chart-subcat', 'signalData'),   # 监听 Vega 信号
     Input('chart-state', 'signalData'),
     Input('chart-customer', 'signalData')],
    [State('store-subcat', 'data'), 
     State('store-state', 'data'),
     State('store-customer', 'data')]
)
def manage_filters(n_clicks, sig_sub, sig_state, sig_cust, curr_sub, curr_state, curr_cust):
    """
    解析 Vega 的 signalData 并更新 Store。
    """
    ctx = callback_context
    if not ctx.triggered:
        return "All", "All", "All"
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 1. 重置逻辑
    if trigger_id == 'btn-reset':
        return "All", "All", "All"

    # 辅助函数：解析 Vega 信号并处理 Toggle (反选)
    def process_signal(signal_data, signal_name, key_name, current_filter):
        # 如果 signal_data 是 None 或者没有对应的 signal_name (通常发生在重置图表时)，不做改变
        if not signal_data or signal_name not in signal_data:
            return current_filter
        
        # 获取 Vega 传递过来的数据列表
        # 结构通常是: {'sel_subcat': {'Sub-Category': ['Chairs']}}
        selection_content = signal_data[signal_name]
        
        # 如果列表为空，说明用户点击空白处取消了选择
        if not selection_content: 
            # 这是一个策略选择：点击空白处是否重置？通常是的。
            # 但为了配合下方的 Toggle 逻辑，我们这里主要看是否有值。
            # 如果 Altair 的 selection 模式是 toggle，第二次点击会发空列表。
            return "All"

        if key_name in selection_content and len(selection_content[key_name]) > 0:
            clicked_val = selection_content[key_name][0]
            # Toggle 逻辑：如果点击的等于当前的 -> 重置
            if str(current_filter) != "All" and str(clicked_val) == str(current_filter):
                return "All"
            return clicked_val
        
        return current_filter

    # 2. 处理各图表点击
    if trigger_id == 'chart-subcat':
        new_sub = process_signal(sig_sub, 'sel_subcat', 'Sub-Category', curr_sub)
        return new_sub, curr_state, curr_cust

    if trigger_id == 'chart-state':
        new_state = process_signal(sig_state, 'sel_state', 'State', curr_state)
        return curr_sub, new_state, curr_cust

    if trigger_id == 'chart-customer':
        new_cust = process_signal(sig_cust, 'sel_cust', 'CustomerName', curr_cust)
        return curr_sub, curr_state, new_cust

    return curr_sub, curr_state, curr_cust


# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 4. LOGIC PART B: VISUALIZATION UPDATES (渲染核心)                             │
# └──────────────────────────────────────────────────────────────────────────────┘
@app.callback(
    [Output('kpi-amount', 'children'),
     Output('kpi-profit', 'children'),
     Output('kpi-quantity', 'children'),
     Output('kpi-orders', 'children'),
     Output('chart-subcat', 'spec'),    # 更新 spec
     Output('chart-state', 'spec'),     # 更新 spec
     Output('chart-customer', 'spec'),  # 更新 spec
     Output('filter-status', 'children')],
    [Input('store-subcat', 'data'),
     Input('store-state', 'data'),
     Input('store-customer', 'data')]
)
def update_visuals(sel_sub, sel_state, sel_cust):
    
    # ── 数据过滤 (与原版逻辑一致) ──
    def filter_df(ignore_sub=False, ignore_state=False, ignore_cust=False):
        d = df.copy()
        if not ignore_sub and sel_sub != "All":
            d = d[d["Sub-Category"] == sel_sub]
        if not ignore_state and sel_state != "All":
            d = d[d["State"] == sel_state]
        if not ignore_cust and sel_cust != "All":
            d = d[d["CustomerName"] == sel_cust]
        return d

    # 计算 KPI
    df_kpi = filter_df()
    if df_kpi.empty:
        k_amt, k_prof, k_qty, k_ords = "$0", "$0", "0", "0"
    else:
        k_amt = f"${df_kpi['Amount'].sum():,.0f}"
        k_prof = f"${df_kpi['Profit'].sum():,.0f}"
        k_qty = f"{df_kpi['Quantity'].sum():,}"
        k_ords = f"{df_kpi['Order ID'].nunique():,}"

    # ── Altair 绘图辅助函数 ──
    # ── Altair 绘图辅助函数 (修复版) ──
    def build_altair_chart(df_in, x_col, y_col, selected_val, signal_name, orientation='v', color_high='#667eea', color_low='#e0e0e0'):
        if df_in.empty:
            return alt.Chart(pd.DataFrame({'text': ['No Data']})).mark_text().encode(text='text').to_dict()

        # 数据聚合逻辑保持不变
        group_col = x_col if orientation == 'v' else y_col
        value_col = y_col if orientation == 'v' else x_col
        
        df_g = df_in.groupby(group_col)[value_col].sum().reset_index()
        df_g = df_g.sort_values(value_col, ascending=False).head(8)

        # ---------------------------------------------------------
        # [关键修复] 1. 构造初始化值
        # 如果当前有选中的值，我们需要告诉 Vega 初始化时就选中它
        # Vega 的 value 格式是一个列表，包含匹配的字段字典
        # ---------------------------------------------------------
        init_value = None
        if selected_val != "All":
            init_value = [{group_col: selected_val}]

        # [关键修复] 2. 定义点击参数时，传入 value
        click_param = alt.selection_point(
            name=signal_name, 
            fields=[group_col],
            value=init_value  # <--- 这里是防止弹回的核心！
        )

        # 3. 定义颜色条件 (视觉反馈)
        # 即便 Vega 内部选中了，我们依然保留这个 Python 控制的颜色逻辑，双重保险
        color_condition = alt.condition(
            alt.datum[group_col] == selected_val,
            alt.value(color_high),
            alt.value(color_low)
        )
        if selected_val == "All":
             color_condition = alt.value(color_high)

        # 4. 基础图表构建
        base = alt.Chart(df_g).encode(
            tooltip=[group_col, value_col]
        ).properties(
            height=280,
            width='container'
        )

        if orientation == 'v':
            chart = base.mark_bar().encode(
                x=alt.X(group_col, sort='-y', axis=alt.Axis(labelAngle=-45, title=None)),
                y=alt.Y(value_col, axis=alt.Axis(title=None)),
                color=color_condition
            )
        else:
            chart = base.mark_bar().encode(
                x=alt.X(value_col, axis=alt.Axis(title=None)),
                y=alt.Y(group_col, sort='-x', axis=alt.Axis(title=None)),
                color=color_condition
            )

        chart = chart.add_params(click_param)
        
        return chart.to_dict()

    # Chart 1: Sub-Category (水平, 紫色)
    df_sub = filter_df(ignore_sub=True)
    fig_sub = build_altair_chart(df_sub, "Profit", "Sub-Category", sel_sub, "sel_subcat", 'h', '#764ba2')

    # Chart 2: State (垂直, 蓝色)
    df_state = filter_df(ignore_state=True)
    fig_state = build_altair_chart(df_state, "State", "Amount", sel_state, "sel_state", 'v', '#667eea')

    # Chart 3: Customer (垂直, 深蓝)
    df_cust = filter_df(ignore_cust=True)
    fig_cust = build_altair_chart(df_cust, "CustomerName", "Amount", sel_cust, "sel_cust", 'v', '#182848')

    status_text = f"Current Filters: Sub-Category='{sel_sub}' | State='{sel_state}' | Customer='{sel_cust}'"

    return k_amt, k_prof, k_qty, k_ords, fig_sub, fig_state, fig_cust, status_text 

if __name__ == "__main__":
    app.run(debug=True, port=8081)
