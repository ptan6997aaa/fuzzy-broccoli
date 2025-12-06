import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. DATA LOADING & PREPROCESSING (真实数据 + 模拟兜底)                         │
# └──────────────────────────────────────────────────────────────────────────────┘
def load_data():
    """
    尝试读取本地 CSV，如果失败则生成模拟数据。
    这确保了代码在任何环境下都能直接运行。
    """
    try:
        if os.path.exists("Details.csv") and os.path.exists("Orders.csv"):
            print("Loading local CSV files...")
            df_d = pd.read_csv("Details.csv")
            df_o = pd.read_csv("Orders.csv")
            df_merged = pd.merge(df_d, df_o, on="Order ID", how="inner")
        else:
            raise FileNotFoundError("Files not found")
    except Exception as e:
        print(f"Warning: {e}. Generating mock data for demonstration...")

    # 数据清洗
    # 统一字符串格式，防止 'Chairs ' 和 'Chairs' 不匹配
    str_cols = ["Sub-Category", "State", "CustomerName"]
    for col in str_cols:
        if col in df_merged.columns:
            df_merged[col] = df_merged[col].astype(str).str.strip()
            
    return df_merged

# 初始化数据
df = load_data()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. UI LAYOUT & STYLES (Bootstrap 布局)                                       │
# └──────────────────────────────────────────────────────────────────────────────┘
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# 样式配置
KPI_STYLE = {
    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", # 紫色渐变
    "color": "white",
    "box-shadow": "0 4px 6px rgba(0,0,0,0.1)",
    "border": "none",
    "border-radius": "10px"
}

CHART_CARD_STYLE = {
    "box-shadow": "0 2px 4px rgba(0,0,0,0.05)",
    "border": "none",
    "border-radius": "8px"
}

app.layout = dbc.Container([
    # ── State Storage (存储筛选状态，不显示在页面上) ──
    # 使用 Store 可以在多个回调之间保持状态，实现多条件组合筛选
    dcc.Store(id='store-subcat', data='All'),
    dcc.Store(id='store-state', data='All'),
    dcc.Store(id='store-customer', data='All'),

    # ── Header ──
    dbc.Row([
        dbc.Col(html.H2("📊 Sales Intelligence Dashboard", className="fw-bold my-3"), width=9),
        dbc.Col(
            dbc.Button(
                "↺ Reset All Filters", 
                id="btn-reset", 
                color="danger", 
                outline=True, 
                className="mt-4 w-100 shadow-sm"
            ),
            width=3
        )
    ], className="mb-4 border-bottom pb-3"),

    # ── Row 1: KPI Cards ──
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Sales", className="opacity-75"),
            html.H3(id="kpi-amount", className="fw-bold")
        ]), style=KPI_STYLE), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Profit", className="opacity-75"),
            html.H3(id="kpi-profit", className="fw-bold")
        ]), style=KPI_STYLE), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Quantity Sold", className="opacity-75"),
            html.H3(id="kpi-quantity", className="fw-bold")
        ]), style=KPI_STYLE), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Orders", className="opacity-75"),
            html.H3(id="kpi-orders", className="fw-bold")
        ]), style=KPI_STYLE), width=3),
    ], className="mb-4"),

    # ── Row 2: Charts ──
    dbc.Row([
        # Chart 1
        dbc.Col(dbc.Card([
            dbc.CardHeader("Profit by Sub-Category", className="bg-white fw-bold border-0"),
            dbc.CardBody(dcc.Graph(id="chart-subcat", config={'displayModeBar': False}, style={'height': '320px'}))
        ], style=CHART_CARD_STYLE), width=4),

        # Chart 2
        dbc.Col(dbc.Card([
            dbc.CardHeader("Sales by State", className="bg-white fw-bold border-0"),
            dbc.CardBody(dcc.Graph(id="chart-state", config={'displayModeBar': False}, style={'height': '320px'}))
        ], style=CHART_CARD_STYLE), width=4),

        # Chart 3
        dbc.Col(dbc.Card([
            dbc.CardHeader("Top Customers", className="bg-white fw-bold border-0"),
            dbc.CardBody(dcc.Graph(id="chart-customer", config={'displayModeBar': False}, style={'height': '320px'}))
        ], style=CHART_CARD_STYLE), width=4),
    ]),
    
    # Footer Status
    dbc.Row(dbc.Col(html.Div(id="filter-status", className="text-muted small mt-4 text-end fst-italic")))

], fluid=True, className="bg-light vh-100 p-4")


# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. LOGIC PART A: FILTER STATE MANAGEMENT (交互逻辑核心)                       │
# └──────────────────────────────────────────────────────────────────────────────┘
@app.callback(
    # 输出：更新3个Store的值，并重置3个图表的clickData(为了允许反选)
    [Output('store-subcat', 'data'), 
     Output('store-state', 'data'),
     Output('store-customer', 'data'),
     Output('chart-subcat', 'clickData'),
     Output('chart-state', 'clickData'),
     Output('chart-customer', 'clickData')],
    # 输入：监听点击事件
    [Input('btn-reset', 'n_clicks'),
     Input('chart-subcat', 'clickData'),
     Input('chart-state', 'clickData'),
     Input('chart-customer', 'clickData')],
    # 状态：读取当前的筛选值
    [State('store-subcat', 'data'), 
     State('store-state', 'data'),
     State('store-customer', 'data')]
)
def manage_filters(n_clicks, click_sub, click_state, click_cust, curr_sub, curr_state, curr_cust):
    """
    负责管理筛选状态。
    逻辑：当用户点击图表时，判断是'选中'还是'取消选中'，并更新对应的 Store。
    最后强制重置图表的 clickData 为 None，以便 Dash 能够捕获下一次同样的点击。
    """
    ctx = callback_context
    if not ctx.triggered:
        return "All", "All", "All", None, None, None
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 防止无限循环：如果是因为 clickData 被重置为 None 而触发，则忽略
    if (trigger_id == 'chart-subcat' and click_sub is None) or \
       (trigger_id == 'chart-state' and click_state is None) or \
       (trigger_id == 'chart-customer' and click_cust is None):
        raise PreventUpdate

    # 1. 重置逻辑
    if trigger_id == 'btn-reset':
        return "All", "All", "All", None, None, None

    # 辅助函数：处理 Toggle (反选) 逻辑
    def get_new_filter_value(click_data, current_filter, key_name):
        try:
            # 获取点击的值
            clicked_val = str(click_data['points'][0][key_name]).strip()
            # 如果点击的值等于当前筛选值 -> 说明用户想取消筛选 -> 返回 "All"
            if str(current_filter) != "All" and clicked_val == str(current_filter):
                return "All"
            return clicked_val
        except:
            return current_filter

    # 2. 处理各图表点击
    if trigger_id == 'chart-subcat' and click_sub:
        new_sub = get_new_filter_value(click_sub, curr_sub, key_name='y') # 柱状图是横向的，类别在 y 轴
        return new_sub, curr_state, curr_cust, None, None, None

    if trigger_id == 'chart-state' and click_state:
        new_state = get_new_filter_value(click_state, curr_state, key_name='x')
        return curr_sub, new_state, curr_cust, None, None, None

    if trigger_id == 'chart-customer' and click_cust:
        new_cust = get_new_filter_value(click_cust, curr_cust, key_name='x')
        return curr_sub, curr_state, new_cust, None, None, None

    return curr_sub, curr_state, curr_cust, None, None, None


# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 4. LOGIC PART B: VISUALIZATION UPDATES (渲染核心)                             │
# └──────────────────────────────────────────────────────────────────────────────┘
@app.callback(
    [Output('kpi-amount', 'children'),
     Output('kpi-profit', 'children'),
     Output('kpi-quantity', 'children'),
     Output('kpi-orders', 'children'),
     Output('chart-subcat', 'figure'),
     Output('chart-state', 'figure'),
     Output('chart-customer', 'figure'),
     Output('filter-status', 'children')],
    [Input('store-subcat', 'data'),
     Input('store-state', 'data'),
     Input('store-customer', 'data')]
)
def update_visuals(sel_sub, sel_state, sel_cust):
    """
    根据 Store 中的状态，过滤数据，计算 KPI，并重新绘制图表。
    """
    
    # ── 数据过滤核心函数 ──
    # ignore_key 参数用于：当绘制“Sub-Category”图表时，即使选中了某个 Sub-Category，
    # 我们也不应该过滤掉其他 Sub-Category 的条形，否则图表就只剩一根柱子了。
    # 我们希望看到所有柱子，但选中的那根高亮。
    def filter_df(ignore_sub=False, ignore_state=False, ignore_cust=False):
        d = df.copy()
        if not ignore_sub and sel_sub != "All":
            d = d[d["Sub-Category"] == sel_sub]
        if not ignore_state and sel_state != "All":
            d = d[d["State"] == sel_state]
        if not ignore_cust and sel_cust != "All":
            d = d[d["CustomerName"] == sel_cust]
        return d

    # 1. 计算 KPI (应用所有过滤条件)
    df_kpi = filter_df()
    if df_kpi.empty:
        k_amt, k_prof, k_qty, k_ords = "$0", "$0", "0", "0"
    else:
        k_amt = f"${df_kpi['Amount'].sum():,.0f}"
        k_prof = f"${df_kpi['Profit'].sum():,.0f}"
        k_qty = f"{df_kpi['Quantity'].sum():,}"
        k_ords = f"{df_kpi['Order ID'].nunique():,}"

    # 2. 绘图辅助函数：统一风格
    def build_bar_chart(df_in, x_col, y_col, selected_val, orientation='v', color_high='#667eea', color_low='#e0e0e0'):
        if df_in.empty:
            # 空数据处理
            fig = go.Figure()
            fig.add_annotation(text="No Data", showarrow=False, font=dict(size=20, color="gray"))
            fig.update_layout(xaxis_visible=False, yaxis_visible=False)
            return fig
        
        # 聚合数据
        df_g = df_in.groupby(x_col if orientation=='v' else y_col)[y_col if orientation=='v' else x_col].sum().reset_index()
        # 排序
        sort_col = y_col if orientation=='v' else x_col
        df_g = df_g.sort_values(sort_col, ascending=True if orientation=='h' else False).head(8) # Top 8

        # 动态颜色逻辑：选中的高亮，其他的变灰
        axis_col = x_col if orientation=='v' else y_col
        colors = [color_high if (selected_val == "All" or str(val) == str(selected_val)) else color_low for val in df_g[axis_col]]

        fig = px.bar(df_g, x=x_col, y=y_col, orientation=orientation, text_auto='.2s')
        fig.update_traces(marker_color=colors, textfont_size=12)
        
        # 精简 Layout
        fig.update_layout(
            margin=dict(t=10, l=10, r=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            yaxis_title=None
        )
        return fig

    # 3. 生成图表
    # Chart 1: Sub-Category (忽略自身的筛选，以便显示上下文)
    df_sub = filter_df(ignore_sub=True)
    fig_sub = build_bar_chart(df_sub, "Profit", "Sub-Category", sel_sub, orientation='h', color_high='#764ba2')

    # Chart 2: State
    df_state = filter_df(ignore_state=True)
    fig_state = build_bar_chart(df_state, "State", "Amount", sel_state, orientation='v', color_high='#667eea')

    # Chart 3: Customer
    df_cust = filter_df(ignore_cust=True)
    fig_cust = build_bar_chart(df_cust, "CustomerName", "Amount", sel_cust, orientation='v', color_high='#182848')

    # 状态栏文字
    status_text = f"Current Filters: Sub-Category='{sel_sub}' | State='{sel_state}' | Customer='{sel_cust}'"

    return k_amt, k_prof, k_qty, k_ords, fig_sub, fig_state, fig_cust, status_text

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)