from dash import Dash, html, dcc, Input, Output, ctx
import pandas as pd
import plotly.express as px

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. 数据加载 (Data Loading)                                                    │
# └──────────────────────────────────────────────────────────────────────────────┘
df_details = pd.read_csv('Details.csv')
df_orders = pd.read_csv('Orders.csv')

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. 数据合并 (Data Merging)                                                    │
# └──────────────────────────────────────────────────────────────────────────────┘
# 使用 pd.merge 进行内连接 (inner join)
# 结果 df_global 只会保留两个表中都有的 Order ID
df_global = pd.merge(df_details, df_orders, on="Order ID", how="inner")

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. 数据清洗 (Data Cleaning)                                                   │
# └──────────────────────────────────────────────────────────────────────────────┘
# 统一格式：转为字符串并去除首尾空格
# 这一步是为了防止 " Electronics " 和 "Electronics" 被统计成两个不同的类别
if "Sub-Category" in df_global.columns:
    df_global["Sub-Category"] = df_global["Sub-Category"].astype(str).str.strip()
if "Category" in df_global.columns:
    df_global["Category"] = df_global["Category"].astype(str).str.strip()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 4. Dash 应用布局配置 (Layout & Styles)                                        │
# └──────────────────────────────────────────────────────────────────────────────┘

# Initialize Dash App 
# 初始化 Dash 应用 
app = Dash(__name__)

# 定义样式 
# 通常有两种方式写样式：
# 1. assets/style.css 文件 (推荐用于大型项目)
# 2. Python 字典 (适合单文件脚本，如下所示) 
styles = {
    'page_container': {'fontFamily': 'sans-serif', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'minHeight': '100vh'},
    'row': {'display': 'flex', 'gap': '16px', 'marginBottom': '20px'},
    'card': {'background': 'white', 'borderRadius': '8px', 'padding': '16px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'flex': '1'},
    'kpi_card': {'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'color': 'white', 'borderRadius': '8px', 'padding': '16px', 'flex': '1'},
    'btn': {'backgroundColor': '#ef4444', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer', 'marginBottom': '20px'}
}

# --- 构建主布局 (Main Layout) ---
# app.layout 是 Dash 的入口 
# Dash 应用的主布局：一个包含标题、KPI 行、图表行的 Div 
app.layout = html.Div(style=styles['page_container'], children=[
    
    # Header
    # html.Div('📊 Sales Overview', style=styles['header']),
    html.H2("📊 Sales Dashboard with Cross-Filtering", style={'textAlign': 'center'}),

    # --- 重置按钮 ---
    # 点击图表会筛选，我们需要一个按钮来"清除筛选"回到全量数据
    html.Button('Reset Filters', id='btn-reset', n_clicks=0, style=styles['btn']), 

    # --- 第一行: KPIs 占位符 (将会被 Callback 更新) ---
    # 注意：这里我们给每个 html.Div 加了 id，以便在 Callback 中识别 
    html.Div(style=styles['row'], children=[
        html.Div(style=styles['kpi_card'], children=[html.Div("Total Amount"), html.Div(id='kpi-1', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
        html.Div(style=styles['kpi_card'], children=[html.Div("Total Profit"), html.Div(id='kpi-2', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
        html.Div(style=styles['kpi_card'], children=[html.Div("Total Quantity"), html.Div(id='kpi-3', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
        html.Div(style=styles['kpi_card'], children=[html.Div("Order Count"), html.Div(id='kpi-4', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
    ]),

    # --- 第二行: 图表 占位符 (将会被 Callback 更新) ---
    # 注意：这里我们给每个 dcc.Graph 加了 id，以便在 Callback 中识别
    html.Div(style=styles['row'], children=[
        html.Div(style=styles['card'], children=[dcc.Graph(id='chart-subcat', style={'height': '300px'})]),
        html.Div(style=styles['card'], children=[dcc.Graph(id='chart-state', style={'height': '300px'})]),
        html.Div(style=styles['card'], children=[dcc.Graph(id='chart-customer', style={'height': '300px'})]),
    ])
])

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 5. 核心逻辑: The Callback                                                     │
# └──────────────────────────────────────────────────────────────────────────────┘
# 这个函数负责所有的交互逻辑
@app.callback(
    # 输出 (Outputs): 我们要更新 4个KPI数字 和 3个图表
    [Output('kpi-1', 'children'), Output('kpi-2', 'children'),
     Output('kpi-3', 'children'), Output('kpi-4', 'children'),
     Output('chart-subcat', 'figure'),
     Output('chart-state', 'figure'),
     Output('chart-customer', 'figure')],
    
    # 输入 (Inputs): 监听 3个图表的点击事件 + 1个重置按钮
    [Input('chart-subcat', 'clickData'),
     Input('chart-state', 'clickData'),
     Input('chart-customer', 'clickData'),
     Input('btn-reset', 'n_clicks')]
)
def update_dashboard(click_subcat, click_state, click_customer, n_clicks):
    
    # [Step A] 确定是谁触发了回调 (Who triggered this?)
    # ctx.triggered_id 获取触发事件的组件 ID
    triggered_id = ctx.triggered_id 
    
    # [Step B] 复制一份数据用于筛选 (不要修改原始全局变量)
    dff = df_global.copy()
    
    # 标题后缀，用来提示用户当前看的是什么数据
    filter_title = " (All Data)"

    # [Step C] 根据触发源进行筛选
    # 逻辑：如果点击了 reset 或 刚打开页面 -> 不筛选
    # 如果点击了某个图表 -> 提取点击的值 -> 筛选 dataframe
    
    if triggered_id == 'chart-subcat' and click_subcat:
        # 获取被点击的柱子的 x 轴值 (Sub-Category Name)
        selected_val = click_subcat['points'][0]['x']
        dff = dff[dff['Sub-Category'] == selected_val]
        filter_title = f" (Filtered by Sub-Category: {selected_val})"
        
    elif triggered_id == 'chart-state' and click_state:
        selected_val = click_state['points'][0]['x']
        dff = dff[dff['State'] == selected_val]
        filter_title = f" (Filtered by State: {selected_val})"
        
    elif triggered_id == 'chart-customer' and click_customer:
        selected_val = click_customer['points'][0]['x']
        dff = dff[dff['CustomerName'] == selected_val]
        filter_title = f" (Filtered by Customer: {selected_val})"

    # [Step D] 基于筛选后的数据 (dff) 重新计算 KPI
    k1 = f"${dff['Amount'].sum():,.0f}"
    k2 = f"${dff['Profit'].sum():,.0f}"
    k3 = f"{dff['Quantity'].sum():,}"
    k4 = f"{dff['Order ID'].nunique():,}"

    # [Step E] 基于筛选后的数据 (dff) 重新生成图表数据源
    # 注意：这里必须重新 groupby，因为数据变了
    
    # Group data for Chart 1
    d_cat = dff.groupby('Sub-Category')['Profit'].sum().reset_index().sort_values('Profit', ascending=False)
    # Group data for Chart 2
    d_state = dff.groupby('State')['Amount'].sum().reset_index().sort_values('Amount', ascending=False).head(10)
    # Group data for Chart 3
    d_cust = dff.groupby('CustomerName')['Amount'].sum().reset_index().sort_values('Amount', ascending=False).head(10)

    # [Step F] 重新绘制图表 (Re-draw Figures)
    # 我们把 title 加上了 filter_title，这样用户知道筛选生效了
    
    fig1 = px.bar(d_cat, x='Sub-Category', y='Profit', title='Profit' + filter_title)
    fig1.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)')
    
    fig2 = px.bar(d_state, x='State', y='Amount', title='Sales by State' + filter_title)
    fig2.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)')
    fig2.update_traces(marker_color='#3b82f6')
    
    fig3 = px.bar(d_cust, x='CustomerName', y='Amount', title='Top Customers' + filter_title)
    fig3.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)')
    fig3.update_traces(marker_color='#10b981')

    # 返回所有 Outputs，顺序必须和装饰器 @app.callback 中的 Output 列表一致
    return k1, k2, k3, k4, fig1, fig2, fig3

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 8. 启动服务器 (Run Server)                                                    │
# └──────────────────────────────────────────────────────────────────────────────┘
if __name__ == '__main__':
    # debug=True: 代码修改后自动刷新页面
    # port=8081: 指定端口
    app.run(debug=True, port=8081) 