# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 1. Imports                                                                   │
# └──────────────────────────────────────────────────────────────────────────────┘
from dash import Dash, html, dcc
import pandas as pd
import altair as alt
import dash_vega_components as dvc

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 2. Data loading & processing                                                 │
# └──────────────────────────────────────────────────────────────────────────────┘
df_details = pd.read_csv('Details.csv')
df_orders = pd.read_csv('Orders.csv')

# --- Data Merging --- 
df_global = pd.merge(df_details, df_orders, on="Order ID", how="inner")

# --- Data Cleaning ---
if "Sub-Category" in df_global.columns:
    df_global["Sub-Category"] = df_global["Sub-Category"].astype(str).str.strip()
if "Category" in df_global.columns:
    df_global["Category"] = df_global["Category"].astype(str).str.strip()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 3. KPI & Chart Data calculations                                                             │
# └──────────────────────────────────────────────────────────────────────────────┘
# --- Calculate Global KPIs ---
total_amount = df_global['Amount'].sum()
total_profit = df_global['Profit'].sum()
total_quantity = df_global['Quantity'].sum()
total_orders = df_global['Order ID'].nunique()

# --- Prepare Chart Data ---
# Chart 1 Data: Profit by Sub-Category
df_sub_cat = df_global.groupby('Sub-Category')['Profit'].sum().reset_index()

# Chart 2 Data: Top 10 States
df_state = df_global.groupby('State')['Amount'].sum().reset_index()
df_state = df_state.sort_values(by='Amount', ascending=False).head(10)

# Chart 3 Data: Top 10 Customers
df_customer = df_global.groupby('CustomerName')['Amount'].sum().reset_index()
df_customer = df_customer.sort_values(by='Amount', ascending=False).head(10)

# ┌────────────────────────────────────────────────────────────────────────────────┐
# │ 4. Configuration & Helper functions (create_kpi_card, create_base_chart, etc.) │
# └────────────────────────────────────────────────────────────────────────────────┘
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

def create_base_chart(data, x_col, y_col, title, color_hex=None, sort_y=True):
    base = alt.Chart(data).encode(
        x=alt.X(x_col, sort='-y' if sort_y else None, axis=alt.Axis(labelAngle=-45)),
        y=y_col,
        tooltip=[x_col, y_col]
    ).properties(
        title=title,
        height=280,
        width='container'
    )
    chart = base.mark_bar(color=color_hex) if color_hex else base.mark_bar()
    return chart.interactive()

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 5. Chart creation (using the helpers)                                        │
# └──────────────────────────────────────────────────────────────────────────────┘
chart1 = create_base_chart(df_sub_cat, 'Sub-Category', 'Profit', 'Profit by Sub-Category')
chart2 = create_base_chart(df_state, 'State', 'Amount', 'Top 10 States by Sales', '#3b82f6')
chart3 = create_base_chart(df_customer, 'CustomerName', 'Amount', 'Top 10 Customers by Sales', '#10b981')

# ┌──────────────────────────────────────────────────────────────────────────────┐
# │ 6. Dash Layout                                                               │
# └──────────────────────────────────────────────────────────────────────────────┘
app = Dash(__name__) 

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
# │ 7. Run server                                                                │
# └──────────────────────────────────────────────────────────────────────────────┘
if __name__ == '__main__':
    app.run(debug=True, port=8081)