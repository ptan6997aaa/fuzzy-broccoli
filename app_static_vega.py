from dash import Dash, html, dcc
import pandas as pd
import altair as alt
import dash_vega_components as dvc

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. 数据加载 (Data Loading)                                                  │
# └──────────────────────────────────────────────────────────────────────────────┘
# Assuming these files exist in your directory
df_details = pd.read_csv('Details.csv')
df_orders = pd.read_csv('Orders.csv')

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. 数据合并 (Data Merging)                                                  │
# └──────────────────────────────────────────────────────────────────────────────┘
df_global = pd.merge(df_details, df_orders, on="Order ID", how="inner")

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. 数据清洗 (Data Cleaning)                                                 │
# └──────────────────────────────────────────────────────────────────────────────┘
if "Sub-Category" in df_global.columns:
    df_global["Sub-Category"] = df_global["Sub-Category"].astype(str).str.strip()
if "Category" in df_global.columns:
    df_global["Category"] = df_global["Category"].astype(str).str.strip()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 4. 计算核心指标 (Calculate Global KPIs)                                     │
# └──────────────────────────────────────────────────────────────────────────────┘
total_amount = df_global['Amount'].sum()
total_profit = df_global['Profit'].sum()
total_quantity = df_global['Quantity'].sum()
total_orders = df_global['Order ID'].nunique()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 5. 准备图表数据 (Prepare Chart Data)                                        │
# └──────────────────────────────────────────────────────────────────────────────┘
# Chart 1 Data: Profit by Sub-Category
df_sub_cat = df_global.groupby('Sub-Category')['Profit'].sum().reset_index()

# Chart 2 Data: Top 10 States
df_state = df_global.groupby('State')['Amount'].sum().reset_index()
df_state = df_state.sort_values(by='Amount', ascending=False).head(10)

# Chart 3 Data: Top 10 Customers
df_customer = df_global.groupby('CustomerName')['Amount'].sum().reset_index()
df_customer = df_customer.sort_values(by='Amount', ascending=False).head(10)

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 6. 使用 Altair 创建 Vega-Lite 图表 (Generate Vega Charts)                    │
# └──────────────────────────────────────────────────────────────────────────────┘

# Helper to keep charts consistent
def create_base_chart(data, x_col, y_col, title, color_hex=None, sort_y=True):
    # Base chart definition
    base = alt.Chart(data).encode(
        # X Axis with sort logic
        x=alt.X(x_col, sort='-y' if sort_y else None, axis=alt.Axis(labelAngle=-45)),
        y=y_col,
        tooltip=[x_col, y_col]
    ).properties(
        title=title,
        height=280, # Fits inside the card height
        width='container' # Responsive width
    )
    
    # Mark definition (Bar)
    if color_hex:
        chart = base.mark_bar(color=color_hex)
    else:
        # Default Altair blue if no color specified
        chart = base.mark_bar()
        
    return chart.interactive()

# --- Chart 1: Profit by Sub-Category ---
# Note: In Vega, we usually sort within the encoding. 
chart1 = create_base_chart(
    df_sub_cat, 
    x_col='Sub-Category', 
    y_col='Profit', 
    title='Profit by Sub-Category'
)

# --- Chart 2: Top 10 States by Sales (Blue) ---
chart2 = create_base_chart(
    df_state, 
    x_col='State', 
    y_col='Amount', 
    title='Top 10 States by Sales', 
    color_hex='#3b82f6'
)

# --- Chart 3: Top 10 Customers by Sales (Green) ---
chart3 = create_base_chart(
    df_customer, 
    x_col='CustomerName', 
    y_col='Amount', 
    title='Top 10 Customers by Sales', 
    color_hex='#10b981'
)

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 7. Dash 应用布局配置 (Layout & Styles)                                      │
# └──────────────────────────────────────────────────────────────────────────────┘

app = Dash(__name__)

styles = {
    'page_container': {
        'fontFamily': 'sans-serif',
        'padding': '20px',
        'backgroundColor': '#f8f9fa',
        'minHeight': '100vh'
    },
    'header': {
        'fontSize': '1.5rem',
        'fontWeight': 'bold',
        'textAlign': 'center',
        'marginBottom': '24px',
        'color': '#1f2937'
    },
    'row': {
        'display': 'flex',
        'flexDirection': 'row',
        'justifyContent': 'space-between',
        'gap': '16px',
        'marginBottom': '32px',
        'paddingLeft': '40px',
        'paddingRight': '40px'
    },
    'kpi_card': {
        'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'color': 'white',
        'borderRadius': '8px',
        'padding': '16px',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
        'flex': '1',
        'textAlign': 'left'
    },
    'kpi_title': {'fontSize': '0.9rem', 'opacity': '0.9'},
    'kpi_value': {'fontSize': '1.8rem', 'fontWeight': 'bold', 'marginTop': '4px'},
    'chart_card': {
        'borderRadius': '8px',
        'padding': '10px', # Increased padding slightly for Vega renderer
        'backgroundColor': 'white',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
        'border': '1px solid #eee',
        'flex': '1',
        'minWidth': '300px',
        'overflow': 'hidden' # Prevents spillover if chart resizes
    }
}

def create_kpi_card(title, value):
    return html.Div(style=styles['kpi_card'], children=[
        html.Div(title, style=styles['kpi_title']),
        html.Div(value, style=styles['kpi_value'])
    ])

# --- Main Layout ---
app.layout = html.Div(style=styles['page_container'], children=[
    
    # Header
    html.Div('📊 Sales Overview (Vega-Lite Version)', style=styles['header']),

    # ROW 1: KPIs
    html.Div(style=styles['row'], children=[
        create_kpi_card('Total Amount', f'${total_amount:,.0f}'),
        create_kpi_card('Total Profit', f'${total_profit:,.0f}'),
        create_kpi_card('Total Quantity', f'{total_quantity:,}'),
        create_kpi_card('Order Count', f'{total_orders:,}')
    ]),

    # ROW 2: Vega-Altair Charts
    html.Div(style=styles['row'], children=[
        # Chart 1
        html.Div(style=styles['chart_card'], children=[
            dvc.Vega(
                id="vega-chart-1",
                spec=chart1.to_dict(), # Convert Altair chart to JSON dict
                opt={"renderer": "svg", "actions": False}, # Hide the "..." menu
                style={'width': '100%'}
            )
        ]),
        # Chart 2
        html.Div(style=styles['chart_card'], children=[
            dvc.Vega(
                id="vega-chart-2",
                spec=chart2.to_dict(),
                opt={"renderer": "svg", "actions": False},
                style={'width': '100%'}
            )
        ]),
        # Chart 3
        html.Div(style=styles['chart_card'], children=[
            dvc.Vega(
                id="vega-chart-3",
                spec=chart3.to_dict(),
                opt={"renderer": "svg", "actions": False},
                style={'width': '100%'}
            )
        ])
    ])
])

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 8. 启动服务器 (Run Server)                                                  │
# └──────────────────────────────────────────────────────────────────────────────┘
if __name__ == '__main__':
    app.run(debug=True, port=8081)