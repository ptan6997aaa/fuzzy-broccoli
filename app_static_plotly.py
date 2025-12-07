# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. Imports                                                                   │
# └──────────────────────────────────────────────────────────────────────────────┘
from dash import Dash, html, dcc
import pandas as pd
import plotly.express as px

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. Data loading & processing                                                 │
# └──────────────────────────────────────────────────────────────────────────────┘
df_details = pd.read_csv('Details.csv')
df_orders = pd.read_csv('Orders.csv')

# --- Data Merging --- 
# 使用 pd.merge 进行内连接 (inner join)
# 结果 df_global 只会保留两个表中都有的 Order ID
df_global = pd.merge(df_details, df_orders, on="Order ID", how="inner")

# --- Data Cleaning ---
# 统一格式：转为字符串并去除首尾空格
# 这一步是为了防止 " Electronics " 和 "Electronics" 被统计成两个不同的类别
if "Sub-Category" in df_global.columns:
    df_global["Sub-Category"] = df_global["Sub-Category"].astype(str).str.strip()
if "Category" in df_global.columns:
    df_global["Category"] = df_global["Category"].astype(str).str.strip()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. KPI & Chart Data calculations                                             │
# └──────────────────────────────────────────────────────────────────────────────┘
# --- Calculate Global KPIs ---
total_amount = df_global['Amount'].sum()
total_profit = df_global['Profit'].sum()
total_quantity = df_global['Quantity'].sum()
total_orders = df_global['Order ID'].nunique()

# --- Prepare Chart Data ---
# Chart 1: Total Profit by Sub-Category (Sorted)
df_sub_cat = df_global.groupby('Sub-Category')['Profit'].sum().reset_index()
df_sub_cat = df_sub_cat.sort_values(by='Profit', ascending=False)

# Chart 2: Total Sales by State (Top 10)
df_state = df_global.groupby('State')['Amount'].sum().reset_index()
df_state = df_state.sort_values(by='Amount', ascending=False).head(10)

# Chart 3: Total Sales by Customer (Top 10)
df_customer = df_global.groupby('CustomerName')['Amount'].sum().reset_index()
df_customer = df_customer.sort_values(by='Amount', ascending=False).head(10)

# ┌────────────────────────────────────────────────────────────────────────────────┐
# │ 4. Configuration & Helper functions (create_kpi_card, create_base_chart, etc.) │
# └────────────────────────────────────────────────────────────────────────────────┘
# Define CSS styles as Python dictionaries (to keep code in one file)
# --- CSS 样式定义 --- 
# 通常有两种方式写样式：
# 1. assets/style.css 文件 (推荐用于大型项目)
# 2. Python 字典 (适合单文件脚本，如下所示) 
styles = {
    'page_container': {
        'fontFamily': 'sans-serif',        # 设置全局字体
        'padding': '20px',                 # 页面内边距
        'backgroundColor': '#f8f9fa',      # 浅灰背景色
        'minHeight': '100vh'               # 最小高度占满屏幕
    },
    'header': {
        'fontSize': '1.5rem',
        'fontWeight': 'bold',
        'textAlign': 'center',
        'marginBottom': '24px',
        'color': '#1f2937'
    },
    # 模拟 Flexbox 行布局 (对应 NiceGUI 的 ui.row())
    'row': {
        'display': 'flex',                 # 启用弹性布局
        'flexDirection': 'row',            # 水平排列
        'justifyContent': 'space-between', # 子元素之间均匀分布
        'gap': '16px',                     # 元素间距
        'marginBottom': '32px',
        'paddingLeft': '40px',             # 左右留白，类似 px-10
        'paddingRight': '40px'
    },
    # KPI 卡片样式 (渐变背景)
    'kpi_card': {
        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'color': 'white',
        'borderRadius': '8px',
        'padding': '16px',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
        'flex': '1',                       # flex: 1 让四个卡片宽度平分
        'textAlign': 'left'
    },
    'kpi_title': {
        'fontSize': '0.9rem',
        'opacity': '0.9'
    },
    'kpi_value': {
        'fontSize': '1.8rem',
        'fontWeight': 'bold',
        'marginTop': '4px'
    },
    # 图表容器卡片
    'chart_card': {
        'borderRadius': '8px',
        'padding': '4px',
        'backgroundColor': 'white',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
        'border': '1px solid #eee',
        'flex': '1',                       # 让三个图表卡片平分宽度
        'minWidth': '300px'                # 防止屏幕太小时图表被压扁
    }
}

# 辅助函数：创建 KPI 卡片
# 避免重复写 KPI 卡片的 html.Div 嵌套
def create_kpi_card(title, value):
    return html.Div(style=styles['kpi_card'], children=[
        html.Div(title, style=styles['kpi_title']),
        html.Div(value, style=styles['kpi_value'])
    ])

# 辅助函数：创建一个 Plotly 柱状图 
def create_plotly_bar_chart(data, x_col, y_col, title, color_hex=None, sort_y=True, template='plotly_white'):
    """
    创建一个 Plotly 柱状图，封装常用配置，便于复用。
    
    参数说明:
    - data: DataFrame, 包含绘图所需的数据。
    - x_col: str, x 轴字段名（如 'Sub-Category'）。
    - y_col: str, y 轴字段名（如 'Profit'）。
    - title: str, 图表标题。
    - color_hex: str(可选),柱子颜色的十六进制值（如 '#3b82f6'），若为 None 则使用默认配色。
    - sort_y: bool(默认 True), 是否按 y 值降序排序 x 轴类别。
    - template: str(默认 'plotly_white'), 图表模板样式。
    
    返回:
    - fig: plotly.graph_objects.Figure 对象，已配置好交互与样式。
    """
    # 如果需要按 y 值降序排序 x 轴类别，则先对数据排序
    if sort_y:
        data = data.sort_values(by=y_col, ascending=False)
    
    # 使用 plotly.express 创建基础柱状图
    fig = px.bar(
        data,
        x=x_col,
        y=y_col,
        title=title,
        template=template
    )
    
    # 设置统一的布局：边距和背景透明
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)'  # 背景透明，适配深色/浅色主题
    )
    
    # 如果指定了颜色，则应用到柱子
    if color_hex:
        fig.update_traces(marker_color=color_hex)
    
    return fig

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 5. Chart creation (using the helpers)                                        │
# └──────────────────────────────────────────────────────────────────────────────┘
fig1 = create_plotly_bar_chart(
    df_sub_cat, 
    x_col='Sub-Category', 
    y_col='Profit', 
    title='Profit by Sub-Category'
)

fig2 = create_plotly_bar_chart(
    df_state, 
    x_col='State', 
    y_col='Amount', 
    title='Top 10 States by Sales', 
    color_hex='#3b82f6'  # 设置柱子颜色蓝色 #3b82f6 
)

fig3 = create_plotly_bar_chart(
    df_customer, 
    x_col='CustomerName', 
    y_col='Amount', 
    title='Top 10 Customers by Sales', 
    color_hex='#10b981'  # 设置柱子颜色绿色 #10b981 
)

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 6. Dash Layout                                                               │
# └──────────────────────────────────────────────────────────────────────────────┘

# Initialize Dash App 
# 初始化 Dash 应用 
app = Dash(__name__)

# --- 构建主布局 (Main Layout) ---
# app.layout 是 Dash 的入口 
# Dash 应用的主布局：一个包含标题、KPI 行、图表行的 Div 
app.layout = html.Div(style=styles['page_container'], children=[
    
    # Header
    html.Div('📊 Sales Overview', style=styles['header']),

    # ROW 1: KPIs
    html.Div(style=styles['row'], children=[
        create_kpi_card('Total Amount', f'${total_amount:,.0f}'),
        create_kpi_card('Total Profit', f'${total_profit:,.0f}'),
        create_kpi_card('Total Quantity', f'{total_quantity:,}'),
        create_kpi_card('Order Count', f'{total_orders:,}')
    ]),

    # ROW 2: Bar Charts 
    # dcc.Graph 是 Dash 的核心组件，用于渲染 Plotly figure 对象 
    html.Div(style=styles['row'], children=[
        # Chart 1
        html.Div(style=styles['chart_card'], children=[
            dcc.Graph(figure=fig1, style={'height': '320px'})
        ]),
        # Chart 2
        html.Div(style=styles['chart_card'], children=[
            dcc.Graph(figure=fig2, style={'height': '320px'})
        ]),
        # Chart 3
        html.Div(style=styles['chart_card'], children=[
            dcc.Graph(figure=fig3, style={'height': '320px'})
        ])
    ])
])

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 7. Run server                                                                │
# └──────────────────────────────────────────────────────────────────────────────┘
if __name__ == '__main__':
    # debug=True: 代码修改后自动刷新页面
    # port=8081: 指定端口
    app.run(debug=True, port=8081) 