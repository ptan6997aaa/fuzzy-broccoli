from dash import Dash, html, dcc, Input, Output, ctx
import pandas as pd
import altair as alt
import dash_vega_components as dvc
from dash import no_update 

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. 数据加载与清洗 (Data Loading & Cleaning)                                   │
# └──────────────────────────────────────────────────────────────────────────────┘
df_details = pd.read_csv('Details.csv')
df_orders = pd.read_csv('Orders.csv')

# Merge
df_global = pd.merge(df_details, df_orders, on="Order ID", how="inner")

# Clean strings
if "Sub-Category" in df_global.columns:
    df_global["Sub-Category"] = df_global["Sub-Category"].astype(str).str.strip()
if "Category" in df_global.columns:
    df_global["Category"] = df_global["Category"].astype(str).str.strip()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. Altair 图表生成辅助函数 (Helper Function)                                  │
# └──────────────────────────────────────────────────────────────────────────────┘
def create_altair_chart(df, x_col, y_col, title, signal_name, color_hex='#636efa'):
    """
    创建一个带有点击交互功能的 Altair 柱状图
    """
    # 1. 定义选择器 (Selection Parameter)
    #    name: 信号名称，必须与 dvc.Vega 中的 signalsToObserve 一致
    #    encodings=['x']: 表示点击时我们要捕获 x轴 的值
    click_sel = alt.selection_point(name=signal_name, encodings=['x'])

    # 2. 构建图表
    chart = alt.Chart(df).mark_bar(color=color_hex).encode(
        x=alt.X(x_col, sort='-y', axis=alt.Axis(labelAngle=-45, title=None)),
        y=alt.Y(y_col, axis=alt.Axis(title=None)),
        tooltip=[x_col, y_col],
        # 3. 条件透明度：虽然我们是重新过滤数据，但加上这个让交互感更好
        opacity=alt.condition(click_sel, alt.value(1), alt.value(0.7))
    ).add_params(
        click_sel  # 4. 必须将 param 添加到图表中
    ).properties(
        title=title,
        height=250, # 适应卡片高度
        width='container'
    )
    return chart.to_dict()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. Dash 应用配置 (App Configuration)                                          │
# └──────────────────────────────────────────────────────────────────────────────┘
app = Dash(__name__)

styles = {
    'page_container': {'fontFamily': 'sans-serif', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'minHeight': '100vh'},
    'row': {'display': 'flex', 'gap': '16px', 'marginBottom': '20px'},
    'card': {'background': 'white', 'borderRadius': '8px', 'padding': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'flex': '1', 'overflow': 'hidden'},
    'kpi_card': {'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'color': 'white', 'borderRadius': '8px', 'padding': '16px', 'flex': '1'},
    'btn': {'backgroundColor': '#ef4444', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer', 'marginBottom': '20px'}
}

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 4. 布局 (Layout) - 使用 dvc.Vega 替代 dcc.Graph                               │
# └──────────────────────────────────────────────────────────────────────────────┘
app.layout = html.Div(style=styles['page_container'], children=[
    
    html.H2("📊 Sales Dashboard (Vega-Altair Version)", style={'textAlign': 'center'}),

    html.Button('Reset Filters', id='btn-reset', n_clicks=0, style=styles['btn']), 

    # --- KPIs ---
    html.Div(style=styles['row'], children=[
        html.Div(style=styles['kpi_card'], children=[html.Div("Total Amount"), html.Div(id='kpi-1', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
        html.Div(style=styles['kpi_card'], children=[html.Div("Total Profit"), html.Div(id='kpi-2', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
        html.Div(style=styles['kpi_card'], children=[html.Div("Total Quantity"), html.Div(id='kpi-3', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
        html.Div(style=styles['kpi_card'], children=[html.Div("Order Count"), html.Div(id='kpi-4', style={'fontSize': '1.8rem', 'fontWeight': 'bold'})]),
    ]),

    # --- Charts ---
    # 注意: signalsToObserve 必须对应 Altair 中定义的 param name
    html.Div(style=styles['row'], children=[
        html.Div(style=styles['card'], children=[
            dvc.Vega(id='chart-subcat', signalsToObserve=['sel_subcat'], style={'width': '100%'})
        ]),
        html.Div(style=styles['card'], children=[
            dvc.Vega(id='chart-state', signalsToObserve=['sel_state'], style={'width': '100%'})
        ]),
        html.Div(style=styles['card'], children=[
            dvc.Vega(id='chart-customer', signalsToObserve=['sel_cust'], style={'width': '100%'})
        ]),
    ])
])

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 5. Callback 逻辑                                                             │
# └──────────────────────────────────────────────────────────────────────────────┘
@app.callback(
    [Output('kpi-1', 'children'), Output('kpi-2', 'children'),
     Output('kpi-3', 'children'), Output('kpi-4', 'children'),
     Output('chart-subcat', 'spec'),
     Output('chart-state', 'spec'),
     Output('chart-customer', 'spec')],
    
    [Input('chart-subcat', 'signalData'),
     Input('chart-state', 'signalData'),
     Input('chart-customer', 'signalData'),
     Input('btn-reset', 'n_clicks')]
)
def update_dashboard(sig_subcat, sig_state, sig_cust, n_clicks):
    
    triggered_id = ctx.triggered_id 
    
    # 默认使用全量数据
    dff = df_global.copy()
    filter_title = " (All Data)"

    # 初始化三个图表的 spec 为 no_update (默认都不刷新)
    # 只有当数据需要改变时，我们才覆盖这个变量
    new_spec_subcat = no_update
    new_spec_state = no_update
    new_spec_cust = no_update

    # --- 逻辑分支 ---

    # 场景 1: 点击了 Reset 按钮 或 刚加载页面
    if not triggered_id or triggered_id == 'btn-reset':
        # 重置时，我们需要强制刷新所有图表回到初始状态
        # 所以这里重新计算所有图表的数据
        d_cat = dff.groupby('Sub-Category')['Profit'].sum().reset_index()
        d_state = dff.groupby('State')['Amount'].sum().reset_index().nlargest(10, 'Amount')
        d_cust = dff.groupby('CustomerName')['Amount'].sum().reset_index().nlargest(10, 'Amount')
        
        new_spec_subcat = create_altair_chart(d_cat, 'Sub-Category', 'Profit', 'Profit', 'sel_subcat', '#636efa')
        new_spec_state = create_altair_chart(d_state, 'State', 'Amount', 'Sales by State', 'sel_state', '#3b82f6')
        new_spec_cust = create_altair_chart(d_cust, 'CustomerName', 'Amount', 'Top Customers', 'sel_cust', '#10b981')

    # 场景 2: 点击了 Chart 1 (Sub-Category)
    elif triggered_id == 'chart-subcat' and sig_subcat:
        signal_content = sig_subcat.get('sel_subcat')
        if signal_content and 'Sub-Category' in signal_content:
            selected_val = signal_content['Sub-Category'][0]
            dff = dff[dff['Sub-Category'] == selected_val] # 筛选数据
            filter_title = f" (Sub-Cat: {selected_val})"
            
            # **关键点**: Chart 1 保持不变 (no_update)，只更新 Chart 2 和 3
            # 计算过滤后的数据给其他图表
            d_state = dff.groupby('State')['Amount'].sum().reset_index().nlargest(10, 'Amount')
            d_cust = dff.groupby('CustomerName')['Amount'].sum().reset_index().nlargest(10, 'Amount')
            
            new_spec_state = create_altair_chart(d_state, 'State', 'Amount', 'Sales by State' + filter_title, 'sel_state', '#3b82f6')
            new_spec_cust = create_altair_chart(d_cust, 'CustomerName', 'Amount', 'Top Customers' + filter_title, 'sel_cust', '#10b981')

    # 场景 3: 点击了 Chart 2 (State)
    elif triggered_id == 'chart-state' and sig_state:
        signal_content = sig_state.get('sel_state')
        if signal_content and 'State' in signal_content:
            selected_val = signal_content['State'][0]
            dff = dff[dff['State'] == selected_val]
            filter_title = f" (State: {selected_val})"

            # **关键点**: Chart 2 保持不变，更新 Chart 1 和 3
            d_cat = dff.groupby('Sub-Category')['Profit'].sum().reset_index()
            d_cust = dff.groupby('CustomerName')['Amount'].sum().reset_index().nlargest(10, 'Amount')

            new_spec_subcat = create_altair_chart(d_cat, 'Sub-Category', 'Profit', 'Profit' + filter_title, 'sel_subcat', '#636efa')
            new_spec_cust = create_altair_chart(d_cust, 'CustomerName', 'Amount', 'Top Customers' + filter_title, 'sel_cust', '#10b981')

    # 场景 4: 点击了 Chart 3 (Customer)
    elif triggered_id == 'chart-customer' and sig_cust:
        signal_content = sig_cust.get('sel_cust')
        if signal_content and 'CustomerName' in signal_content:
            selected_val = signal_content['CustomerName'][0]
            dff = dff[dff['CustomerName'] == selected_val]
            filter_title = f" (Customer: {selected_val})"

            # **关键点**: Chart 3 保持不变，更新 Chart 1 和 2
            d_cat = dff.groupby('Sub-Category')['Profit'].sum().reset_index()
            d_state = dff.groupby('State')['Amount'].sum().reset_index().nlargest(10, 'Amount')

            new_spec_subcat = create_altair_chart(d_cat, 'Sub-Category', 'Profit', 'Profit' + filter_title, 'sel_subcat', '#636efa')
            new_spec_state = create_altair_chart(d_state, 'State', 'Amount', 'Sales by State' + filter_title, 'sel_state', '#3b82f6')

    # --- 计算 KPI (KPI 总是要更新的) ---
    k1 = f"${dff['Amount'].sum():,.0f}"
    k2 = f"${dff['Profit'].sum():,.0f}"
    k3 = f"{dff['Quantity'].sum():,}"
    k4 = f"{dff['Order ID'].nunique():,}"

    return k1, k2, k3, k4, new_spec_subcat, new_spec_state, new_spec_cust

if __name__ == '__main__':
    app.run(debug=True, port=8081)