import dash
from dash import dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. 数据加载与清洗模块 (Data Loading & Cleaning)                               │
# └──────────────────────────────────────────────────────────────────────────────┘          
df_d = pd.read_csv("Details.csv")
df_o = pd.read_csv("Orders.csv")
df_merged = pd.merge(df_d, df_o, on="Order ID", how="inner")

# 清洗数据：去除货币符号($)和千分位(,)，强制转为 float
# 这一步是为了防止 pandas 将 "$1,200" 识别为字符串导致 sum() 报错
numeric_cols = ['Amount', 'Profit', 'Quantity']
for col in numeric_cols:
    if col in df_merged.columns and df_merged[col].dtype == 'object':
        df_merged[col] = df_merged[col].astype(str).str.replace(r'[$,]', '', regex=True)
        df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce').fillna(0)

# 初始化全局数据
df = df_merged 

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. 辅助函数库 (Helper Functions)                                              │
# └──────────────────────────────────────────────────────────────────────────────┘

def create_kpi_card(title, value_id, icon="📊"):
    """生成统一风格的 KPI 卡片"""
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.Div([
            html.H6(title, className="text-uppercase small opacity-75 mb-0"),
            html.Span(icon, className="float-end fs-4 opacity-50")
        ]),
        html.H3(id=value_id, className="fw-bold mt-2 mb-0")
    ]), className="h-100 shadow-sm border-0", 
    style={"background": "linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)", "color": "#333"}), 
    width=6, lg=3, className="mb-3")

def build_interactive_bar(df_in, x_col, y_col, selected_val, active_color, title, orientation='v'):
    """
    通用交互式柱状图生成函数：
    1. 处理空数据
    2. 处理高亮逻辑 (Highlighting)
    3. 处理横向/纵向布局
    """
    if df_in.empty:
        # 空状态处理
        fig = go.Figure()
        fig.add_annotation(text="No Data", showarrow=False, font=dict(size=20, color="gray"))
        fig.update_layout(xaxis_visible=False, yaxis_visible=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    # 聚合数据
    if orientation == 'v':
        # 垂直图：x是类别，y是数值 (取前10)
        df_grouped = df_in.groupby(x_col)[y_col].sum().reset_index().sort_values(y_col, ascending=False).head(10)
        plot_x, plot_y = x_col, y_col
    else:
        # 水平图：y是类别，x是数值 (取后10以保证绘图从上到下顺序)
        df_grouped = df_in.groupby(y_col)[x_col].sum().reset_index().sort_values(x_col, ascending=True).tail(10)
        plot_x, plot_y = x_col, y_col

    # 动态颜色逻辑: 选中的柱子用 active_color，其他的变灰
    cat_col = x_col if orientation == 'v' else y_col
    colors = [active_color if (str(selected_val) == "All" or str(val) == str(selected_val)) else '#e0e0e0' for val in df_grouped[cat_col]]

    fig = px.bar(df_grouped, x=plot_x, y=plot_y, text_auto='.2s', orientation=orientation, title=title)
    fig.update_traces(marker_color=colors, hovertemplate='%{y}: %{x}<extra></extra>')
    
    # 极简布局
    fig.update_layout(
        margin=dict(t=40, l=20, r=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, sans-serif"),
        title_font_size=14
    )
    return fig

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. App Layout (UI 布局)                                                       │
# └──────────────────────────────────────────────────────────────────────────────┘
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    # ── Store 组件：用于存储当前的筛选状态 ──
    dcc.Store(id='store-subcat', data='All'),
    dcc.Store(id='store-state', data='All'),
    dcc.Store(id='store-customer', data='All'),

    # ── Header ──
    dbc.Row([
        dbc.Col([
            html.H2("🚀 Sales Analytics Dashboard", className="fw-bold"),
            html.P("Interactive cross-filtering: Click bars to filter data.", className="text-muted")
        ], width=9),
        dbc.Col([
            dbc.Button("↺ Reset Filters", id="clear-btn", color="dark", outline=True, className="mt-3 w-100 shadow-sm")
        ], width=3)
    ], className="py-4 mb-3 border-bottom"),

    # ── Row 1: KPIs ──
    dbc.Row([
        create_kpi_card("Total Amount", "kpi-amount", "💰"),
        create_kpi_card("Total Profit", "kpi-profit", "📈"),
        create_kpi_card("Total Quantity", "kpi-quantity", "📦"),
        create_kpi_card("Order Count", "kpi-orders", "🛒"),
    ]),

    # ── Row 2: Charts (with Loading Spinners) ──
    dbc.Row([
        # Chart 1: Profit by Sub-Category (Horizontal)
        dbc.Col(dbc.Card([
             dcc.Loading(dcc.Graph(id="chart-subcat", style={'height': '350px'}, config={'displayModeBar': False}))
        ], className="border-0 shadow-sm h-100 p-2"), width=12, md=4),
        
        # Chart 2: Sales by State (Vertical)
        dbc.Col(dbc.Card([
             dcc.Loading(dcc.Graph(id="chart-state", style={'height': '350px'}, config={'displayModeBar': False}))
        ], className="border-0 shadow-sm h-100 p-2"), width=12, md=4),
        
        # Chart 3: Top Customers (Vertical)
        dbc.Col(dbc.Card([
             dcc.Loading(dcc.Graph(id="chart-customer", style={'height': '350px'}, config={'displayModeBar': False}))
        ], className="border-0 shadow-sm h-100 p-2"), width=12, md=4),
    ], className="gy-4"),

    # ── Footer ──
    dbc.Row(dbc.Col(html.Div(id="filter-status", className="text-center text-muted small mt-4")))

], fluid=True, className="bg-light min-vh-100")

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 4. Callbacks (交互逻辑)                                                       │
# └──────────────────────────────────────────────────────────────────────────────┘

# ── Callback 1: 管理筛选状态 (State Management) ──
# 负责处理点击事件，更新 dcc.Store，并重置图表的 clickData
@app.callback(
    [Output('store-subcat', 'data'), 
     Output('store-state', 'data'),
     Output('store-customer', 'data'),
     Output('chart-subcat', 'clickData'), # 用于重置
     Output('chart-state', 'clickData'),  # 用于重置
     Output('chart-customer', 'clickData')], # 用于重置
    [Input('clear-btn', 'n_clicks'),
     Input('chart-subcat', 'clickData'),
     Input('chart-state', 'clickData'),
     Input('chart-customer', 'clickData')],
    [State('store-subcat', 'data'), 
     State('store-state', 'data'),
     State('store-customer', 'data')]
)
def manage_state(n_clicks, c_sub, c_state, c_cust, s_sub, s_state, s_cust):
    ctx = callback_context
    if not ctx.triggered:
        return "All", "All", "All", None, None, None
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # 1. 防止死循环：如果是被重置为 None 触发的，直接忽略
    if "chart" in trigger_id and ctx.triggered[0]['value'] is None:
        raise PreventUpdate

    # 2. 清除所有筛选
    if trigger_id == 'clear-btn':
        return "All", "All", "All", None, None, None

    # 3. 处理图表点击 (Toggle 逻辑)
    # 如果点击了已选中的值 -> 取消选中(回到All)；否则 -> 选中新值
    def get_next_state(click_data, current_state, key='x'):
        if not click_data: return current_state
        try:
            clicked_val = click_data['points'][0][key]
            if str(clicked_val) == str(current_state):
                return "All" # Toggle Off
            return clicked_val # Toggle On
        except:
            return current_state

    # 注意：Sub-Category 是水平图，Category 轴在 y 轴
    if trigger_id == 'chart-subcat':
        new_sub = get_next_state(c_sub, s_sub, key='y')
        return new_sub, s_state, s_cust, None, None, None
    
    # State 是垂直图，State 轴在 x 轴
    if trigger_id == 'chart-state':
        new_state = get_next_state(c_state, s_state, key='x')
        return s_sub, new_state, s_cust, None, None, None
    
    # Customer 是垂直图，Customer 轴在 x 轴
    if trigger_id == 'chart-customer':
        new_cust = get_next_state(c_cust, s_cust, key='x')
        return s_sub, s_state, new_cust, None, None, None

    return s_sub, s_state, s_cust, None, None, None

# ── Callback 2: 更新 UI (View Rendering) ──
# 负责根据 dcc.Store 中的状态，过滤数据并重新绘制图表和 KPI
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
def update_view(sel_sub, sel_state, sel_cust):
    try:
        # 1. 准备基础数据 (Copy一份，避免修改全局 df)
        dff = df.copy()

        # 2. 计算 KPI (Intersection: 取所有筛选的交集)
        # ------------------------------------------------
        dff_kpi = dff.copy()
        if sel_sub != "All": dff_kpi = dff_kpi[dff_kpi["Sub-Category"] == sel_sub]
        if sel_state != "All": dff_kpi = dff_kpi[dff_kpi["State"] == sel_state]
        if sel_cust != "All": dff_kpi = dff_kpi[dff_kpi["CustomerName"] == sel_cust]
        
        if dff_kpi.empty:
            kpis = ("$0", "$0", "0", "0")
        else:
            kpis = (
                f"${dff_kpi['Amount'].sum():,.0f}",
                f"${dff_kpi['Profit'].sum():,.0f}",
                f"{dff_kpi['Quantity'].sum():,}",
                f"{dff_kpi['Order ID'].nunique():,}"
            )

        # 3. 准备图表数据 (Context Filtering: 上下文过滤)
        # ------------------------------------------------
        # 逻辑：选中 "California" 时，State 图表应该显示所有州(以便切换)，但高亮 "California"。
        # 但 State 图表的数据应该受到 "Sub-Category" 和 "Customer" 的影响。
        
        # A. Sub-Category 图表数据 (过滤条件：State + Customer)
        df_sub = dff.copy()
        if sel_state != "All": df_sub = df_sub[df_sub["State"] == sel_state]
        if sel_cust != "All": df_sub = df_sub[df_sub["CustomerName"] == sel_cust]
        
        # B. State 图表数据 (过滤条件：Sub + Customer)
        df_state = dff.copy()
        if sel_sub != "All": df_state = df_state[df_state["Sub-Category"] == sel_sub]
        if sel_cust != "All": df_state = df_state[df_state["CustomerName"] == sel_cust]
        
        # C. Customer 图表数据 (过滤条件：Sub + State)
        df_cust = dff.copy()
        if sel_sub != "All": df_cust = df_cust[df_cust["Sub-Category"] == sel_sub]
        if sel_state != "All": df_cust = df_cust[df_cust["State"] == sel_state]

        # 4. 生成图表
        # ------------------------------------------------
        fig_sub = build_interactive_bar(
            df_sub, x_col='Profit', y_col='Sub-Category', 
            selected_val=sel_sub, active_color='#764ba2', title="Profit by Sub-Category", orientation='h'
        )
        
        fig_state = build_interactive_bar(
            df_state, x_col='State', y_col='Amount', 
            selected_val=sel_state, active_color='#667eea', title="Sales by State", orientation='v'
        )
        
        fig_cust = build_interactive_bar(
            df_cust, x_col='CustomerName', y_col='Amount', 
            selected_val=sel_cust, active_color='#182848', title="Top Customers", orientation='v'
        )

        status_text = f"Current Filters: Sub-Cat='{sel_sub}' | State='{sel_state}' | Customer='{sel_cust}'"

        return *kpis, fig_sub, fig_state, fig_cust, status_text

    except Exception as e:
        print(f"❌ Error in update_view: {e}")
        # 出错时返回默认空值，防止页面崩溃
        return "$0", "$0", "0", "0", go.Figure(), go.Figure(), go.Figure(), f"Error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True, port=8050)