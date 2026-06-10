"""
Professional Trading Terminal for AI Quant Hedge Fund
Bloomberg-style dark theme with interactive charts and real-time data
"""

import dash
from dash import dcc, html, callback, Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from src.monitoring.portfolio_models import Portfolio, Position, Trade, OrderSide
    from src.modes.mode_manager import TradingMode, ModeManager
    from src.execution.mt5_broker import MT5Broker
    HAS_CORE = True
except ImportError:
    HAS_CORE = False


COLORS = {
    'background': '#0d1117',
    'panel': '#161b22',
    'border': '#30363d',
    'text': '#c9d1d9',
    'text_muted': '#8b949e',
    'accent': '#58a6ff',
    'success': '#3fb950',
    'danger': '#f85149',
    'warning': '#d29922',
    'buy': '#238636',
    'sell': '#da3633',
    'chart_up': '#26a269',
    'chart_down': '#f66151',
    'grid': '#21262d'
}


app = dash.Dash(__name__, title="AI Quant Hedge Fund Terminal", update_title=None)


def create_panel(title, children, height=None):
    style = {
        'backgroundColor': COLORS['panel'],
        'border': f'1px solid {COLORS["border"]}',
        'borderRadius': '4px',
        'padding': '10px',
        'margin': '5px',
        'height': height or 'auto',
        'overflow': 'hidden'
    }
    title_style = {
        'color': COLORS['accent'],
        'font-size': '11px',
        'font-weight': 'bold',
        'text-transform': 'uppercase',
        'margin-bottom': '8px',
        'letter-spacing': '1px'
    }
    return html.Div([
        html.Div(title, style=title_style),
        html.Div(children, style={'overflow': 'auto', 'height': '100%'})
    ], style=style)


def create_metric_card(label, value, change=None, color=None):
    value_style = {
        'font-size': '20px',
        'font-weight': 'bold',
        'color': color or COLORS['text']
    }
    label_style = {
        'font-size': '10px',
        'color': COLORS['text_muted'],
        'text-transform': 'uppercase'
    }
    change_style = {
        'font-size': '11px',
        'color': COLORS['success'] if change and change > 0 else COLORS['danger'] if change and change < 0 else COLORS['text_muted']
    }
    return html.Div([
        html.Div(label, style=label_style),
        html.Div(f"{value:,.2f}" if isinstance(value, (int, float)) else value, style=value_style),
        html.Div(f"{change:+.2f}%" if change else "", style=change_style) if change is not None else None
    ], style={'padding': '5px'})


def create_position_row(position):
    pnl = position.get('pnl', 0)
    pnl_pct = position.get('pnl_pct', 0)
    return html.Div([
        html.Span(position.get('symbol', ''), style={'width': '80px', 'font-weight': 'bold'}),
        html.Span(position.get('side', ''), style={
            'width': '50px', 'color': COLORS['buy'] if position.get('side') == 'BUY' else COLORS['sell'],
            'font-weight': 'bold'
        }),
        html.Span(f"{position.get('volume', 0):.2f}", style={'width': '60px', 'text-align': 'right'}),
        html.Span(f"{position.get('open_price', 0):.5f}", style={'width': '80px', 'text-align': 'right'}),
        html.Span(f"{position.get('current_price', 0):.5f}", style={'width': '80px', 'text-align': 'right'}),
        html.Span(f"${pnl:+.2f}", style={
            'width': '80px', 'text-align': 'right',
            'color': COLORS['success'] if pnl >= 0 else COLORS['danger'], 'font-weight': 'bold'
        }),
        html.Span(f"{pnl_pct:+.2f}%", style={
            'width': '70px', 'text-align': 'right',
            'color': COLORS['success'] if pnl_pct >= 0 else COLORS['danger']
        }),
        html.Span(f"{position.get('sl', '-')}/{position.get('tp', '-')}", style={'width': '100px', 'text-align': 'center', 'color': COLORS['text_muted']}),
    ], style={'display': 'flex', 'padding': '8px 5px', 'border-bottom': f'1px solid {COLORS["border"]}', 'align-items': 'center'})


def create_signal_row(signal):
    signal_color = COLORS['buy'] if signal.get('signal') == 'BUY' else COLORS['sell'] if signal.get('signal') == 'SELL' else COLORS['text_muted']
    return html.Div([
        html.Span(signal.get('strategy', '')[:20], style={'width': '150px', 'font-size': '11px'}),
        html.Span(signal.get('signal', ''), style={'width': '60px', 'color': signal_color, 'font-weight': 'bold', 'text-align': 'center'}),
        html.Div([
            html.Div(style={'width': f"{signal.get('confidence', 0) * 100}%", 'height': '6px', 'backgroundColor': signal_color, 'borderRadius': '3px'}),
            html.Span(f"{signal.get('confidence', 0):.0%}", style={'font-size': '10px', 'margin-left': '5px'})
        ], style={'width': '80px', 'display': 'flex', 'align-items': 'center'}),
    ], style={'display': 'flex', 'padding': '6px 5px', 'border-bottom': f'1px solid {COLORS["border"]}', 'align-items': 'center'})


def create_candlestick_chart(df, symbol="EURUSD"):
    if df is None or df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name=symbol, increasing_line_color=COLORS['chart_up'], decreasing_line_color=COLORS['chart_down'],
        increasing_fillcolor=COLORS['chart_up'], decreasing_fillcolor=COLORS['chart_down']
    ))
    if 'sma20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['sma20'], mode='lines', name='SMA20', line=dict(color='#58a6ff', width=1)))
    if 'sma50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['sma50'], mode='lines', name='SMA50', line=dict(color='#d29922', width=1)))
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=30, b=10), height=350,
        xaxis=dict(showgrid=True, gridcolor=COLORS['grid'], rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor=COLORS['grid']),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        dragmode='zoom'
    )
    return fig


def create_equity_curve(trades):
    if not trades:
        return go.Figure()
    df = pd.DataFrame(trades)
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df = df.sort_values('exit_time')
    df['cumulative_pnl'] = df['pnl'].cumsum()
    df['equity'] = 100000 + df['cumulative_pnl']
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['exit_time'], y=df['equity'], mode='lines+markers', name='Equity',
        line=dict(color=COLORS['accent'], width=2), marker=dict(size=4)
    ))
    fig.add_hline(y=100000, line_dash='dash', line_color=COLORS['text_muted'], annotation_text="Initial")
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=30, b=10), height=180,
        xaxis=dict(showgrid=True, gridcolor=COLORS['grid']),
        yaxis=dict(showgrid=True, gridcolor=COLORS['grid'])
    )
    return fig


def create_portfolio_pie(positions):
    if not positions:
        return go.Figure()
    labels = [p.get('symbol', '') for p in positions]
    values = [abs(p.get('pnl', 0)) for p in positions]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5, marker=dict(colors=['#238636', '#58a6ff', '#d29922', '#a371f7', '#f66151']))])
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10),
        height=180, showlegend=True, legend=dict(orientation='h', yanchor='bottom', y=-0.3)
    )
    return fig


def generate_demo_data():
    import random
    now = datetime.now()
    times = [now - timedelta(minutes=5*i) for i in range(200)]
    base_price = 1.0850
    prices = []
    for _ in range(200):
        change = random.uniform(-0.0005, 0.0005)
        base_price += change
        prices.append(base_price)
    df = pd.DataFrame({
        'time': times, 'open': prices,
        'close': [p + random.uniform(-0.0002, 0.0002) for p in prices],
        'high': [p + random.uniform(0, 0.0005) for p in prices],
        'low': [p - random.uniform(0, 0.0005) for p in prices],
        'volume': [random.randint(1000, 10000) for _ in range(200)]
    })
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    positions = [
        {'ticket': 123456, 'symbol': 'EURUSD', 'side': 'BUY', 'volume': 1.0, 'open_price': 1.0850, 'current_price': 1.0875, 'pnl': 250.00, 'pnl_pct': 2.31, 'sl': 1.0750, 'tp': 1.1000},
        {'ticket': 123457, 'symbol': 'GBPUSD', 'side': 'BUY', 'volume': 0.5, 'open_price': 1.2700, 'current_price': 1.2750, 'pnl': 125.00, 'pnl_pct': 1.97, 'sl': 1.2650, 'tp': 1.2800},
        {'ticket': 123458, 'symbol': 'USDJPY', 'side': 'SELL', 'volume': 0.75, 'open_price': 149.50, 'current_price': 149.75, 'pnl': -93.75, 'pnl_pct': -0.83, 'sl': 150.50, 'tp': 147.00}
    ]
    signals = [
        {'strategy': 'ICT SMC', 'signal': 'BUY', 'confidence': 0.72},
        {'strategy': 'Price Action', 'signal': 'BUY', 'confidence': 0.68},
        {'strategy': 'RSI Divergence', 'signal': 'BUY', 'confidence': 0.65},
        {'strategy': 'MA Crossover', 'signal': 'HOLD', 'confidence': 0.55},
        {'strategy': 'MACD Crossover', 'signal': 'BUY', 'confidence': 0.70},
        {'strategy': 'Bollinger Bands', 'signal': 'SELL', 'confidence': 0.62},
        {'strategy': 'Fibonacci', 'signal': 'BUY', 'confidence': 0.58},
        {'strategy': 'Volume Spike', 'signal': 'HOLD', 'confidence': 0.52},
        {'strategy': 'Order Block', 'signal': 'BUY', 'confidence': 0.75},
        {'strategy': 'Liquidity Sweep', 'signal': 'SELL', 'confidence': 0.60}
    ]
    trades_history = [
        {'exit_time': now - timedelta(days=1), 'pnl': 150.00},
        {'exit_time': now - timedelta(days=2), 'pnl': -75.00},
        {'exit_time': now - timedelta(days=3), 'pnl': 200.00},
        {'exit_time': now - timedelta(days=4), 'pnl': 100.00},
        {'exit_time': now - timedelta(days=5), 'pnl': -50.00},
        {'exit_time': now - timedelta(days=6), 'pnl': 180.00},
        {'exit_time': now - timedelta(days=7), 'pnl': 90.00}
    ]
    watchlist = [
        {'symbol': 'EURUSD', 'bid': 1.0875, 'ask': 1.0878, 'change': 0.15},
        {'symbol': 'GBPUSD', 'bid': 1.2750, 'ask': 1.2753, 'change': 0.22},
        {'symbol': 'USDJPY', 'bid': 149.75, 'ask': 149.78, 'change': -0.10},
        {'symbol': 'AUDUSD', 'bid': 0.6520, 'ask': 0.6523, 'change': 0.08},
        {'symbol': 'USDCAD', 'bid': 1.3650, 'ask': 1.3653, 'change': -0.05},
        {'symbol': 'XAUUSD', 'bid': 2025.50, 'ask': 2026.00, 'change': 0.45}
    ]
    return df, positions, signals, trades_history, watchlist


app.layout = html.Div([
    dcc.Interval(id='update-interval', interval=3000, n_intervals=0),
    dcc.Store(id='stored-data', data={}),
    html.Div([
        html.Div([html.Span("AI QUANT HEDGE FUND", style={'font-weight': 'bold', 'font-size': '16px', 'color': COLORS['accent']}),
                  html.Span(" v2.0", style={'color': COLORS['text_muted'], 'font-size': '12px'})],
                 style={'display': 'flex', 'align-items': 'center'}),
        html.Div([html.Span(id='current-time', style={'color': COLORS['text_muted'], 'margin-right': '15px'}),
                  html.Span("CONNECTED", style={'color': COLORS['success'], 'font-size': '10px', 'margin-right': '5px'}),
                  html.Span("●", style={'color': COLORS['success']})], style={'display': 'flex', 'align-items': 'center'}),
        html.Div([
            html.Button("ANALYZE", id='btn-analyze', n_clicks=0, style={
                'backgroundColor': COLORS['accent'], 'border': 'none', 'color': 'white',
                'padding': '8px 16px', 'borderRadius': '4px', 'cursor': 'pointer', 'margin-right': '8px', 'font-size': '11px', 'font-weight': 'bold'
            }),
            html.Button("SETTINGS", id='btn-settings', n_clicks=0, style={
                'backgroundColor': COLORS['panel'], 'border': f'1px solid {COLORS["border"]}', 'color': COLORS['text'],
                'padding': '8px 16px', 'borderRadius': '4px', 'cursor': 'pointer', 'font-size': '11px'
            }),
        ], style={'display': 'flex'}),
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '10px 15px',
              'backgroundColor': COLORS['panel'], 'borderBottom': f'1px solid {COLORS["border"]}'}),
    html.Div([
        html.Div([create_metric_card("Portfolio", "126,789.45", 1.2, COLORS['success']),
                  create_metric_card("Daily PnL", "1,234.56", 0.98, COLORS['success']),
                  create_metric_card("Win Rate", "68%", None, COLORS['accent']),
                  create_metric_card("Profit Factor", "2.34", None, COLORS['success']),
                  create_metric_card("Positions", "3", None, COLORS['text']),
                  create_metric_card("Margin", "845%", None, COLORS['success'])],
                 style={'display': 'flex', 'flex-wrap': 'wrap', 'gap': '5px'}),
    ], style={'padding': '10px', 'backgroundColor': COLORS['background'], 'borderBottom': f'1px solid {COLORS["border"]}'}),
    html.Div([
        html.Div([create_panel("CHARTS", dcc.Graph(id='main-chart', style={'height': '350px'}))], style={'width': '70%'}),
        html.Div([create_panel("POSITIONS", html.Div(id='positions-list')),
                  create_panel("WATCHLIST", html.Div(id='watchlist-panel'))], style={'width': '30%'}),
    ], style={'display': 'flex', 'padding': '5px'}),
    html.Div([
        html.Div([create_panel("STRATEGY SIGNALS", html.Div(id='signals-list'))], style={'width': '50%'}),
        html.Div([create_panel("PERFORMANCE", dcc.Graph(id='equity-chart', style={'height': '180px'}))], style={'width': '25%'}),
        html.Div([create_panel("ALLOCATION", dcc.Graph(id='pie-chart', style={'height': '180px'}))], style={'width': '25%'}),
    ], style={'display': 'flex', 'padding': '5px'}),
    html.Div([
        html.Div([html.Span("MODE:", style={'color': COLORS['text_muted'], 'margin-right': '5px', 'font-size': '11px'}),
                  dcc.Dropdown(id='mode-selector',
                               options=[{'label': 'MANUAL', 'value': 'manual'}, {'label': 'SEMI-AUTO', 'value': 'semi_auto'}, {'label': 'FULL-AUTO', 'value': 'full_auto'}],
                               value='semi_auto', clearable=False,
                               style={'width': '130px', 'color': COLORS['text'], 'font-size': '11px'})],
                 style={'display': 'flex', 'alignItems': 'center', 'margin-right': '20px'}),
        html.Div([html.Span("SYMBOL:", style={'color': COLORS['text_muted'], 'margin-right': '5px', 'font-size': '11px'}),
                  dcc.Dropdown(id='symbol-selector',
                               options=[{'label': 'EURUSD', 'value': 'EURUSD'}, {'label': 'GBPUSD', 'value': 'GBPUSD'}, {'label': 'USDJPY', 'value': 'USDJPY'},
                                        {'label': 'AUDUSD', 'value': 'AUDUSD'}, {'label': 'XAUUSD', 'value': 'XAUUSD'}],
                               value='EURUSD', clearable=False,
                               style={'width': '110px', 'color': COLORS['text'], 'font-size': '11px'})],
                 style={'display': 'flex', 'alignItems': 'center', 'margin-right': '20px'}),
        html.Div([html.Span("TIMEFRAME:", style={'color': COLORS['text_muted'], 'margin-right': '5px', 'font-size': '11px'}),
                  dcc.Dropdown(id='timeframe-selector',
                               options=[{'label': '1m', 'value': '1m'}, {'label': '5m', 'value': '5m'}, {'label': '15m', 'value': '15m'},
                                        {'label': '1H', 'value': '1H'}, {'label': '4H', 'value': '4H'}, {'label': '1D', 'value': '1D'}],
                               value='1m', clearable=False,
                               style={'width': '80px', 'color': COLORS['text'], 'font-size': '11px'})],
                 style={'display': 'flex', 'alignItems': 'center'}),
    ], style={'display': 'flex', 'padding': '10px 15px', 'backgroundColor': COLORS['panel'], 'borderTop': f'1px solid {COLORS["border"]}'}),
], style={'backgroundColor': COLORS['background'], 'min-height': '100vh', 'font-family': "'SF Mono', 'Consolas', monospace", 'font-size': '12px'})


@callback([Output('stored-data', 'data'), Output('current-time', 'children')],
          [Input('update-interval', 'n_intervals'), Input('btn-analyze', 'n_clicks')])
def update_data(n_intervals, n_clicks):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df, positions, signals, trades_history, watchlist = generate_demo_data()
    return {'chart_data': df.to_dict('records'), 'positions': positions, 'signals': signals,
            'trades_history': trades_history, 'watchlist': watchlist}, now


@callback([Output('main-chart', 'figure'), Output('positions-list', 'children'), Output('signals-list', 'children'),
          Output('watchlist-panel', 'children'), Output('equity-chart', 'figure'), Output('pie-chart', 'figure')],
         [Input('stored-data', 'data'), Input('symbol-selector', 'value')])
def update_charts(data, symbol):
    if not data:
        return go.Figure(), "", "", "", go.Figure(), go.Figure()
    chart_df = pd.DataFrame(data['chart_data'])
    chart_fig = create_candlestick_chart(chart_df, symbol)
    positions_list = [create_position_row(p) for p in data['positions']]
    positions_list.insert(0, html.Div([
        html.Span("SYMBOL", style={'width': '80px', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("SIDE", style={'width': '50px', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("VOL", style={'width': '60px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("ENTRY", style={'width': '80px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("CURRENT", style={'width': '80px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("PNL", style={'width': '80px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("PCT", style={'width': '70px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("SL/TP", style={'width': '100px', 'text-align': 'center', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
    ], style={'display': 'flex', 'padding-bottom': '8px', 'border-bottom': f'2px solid {COLORS["border"]}'}))
    signals_list = [create_signal_row(s) for s in data['signals']]
    signals_list.insert(0, html.Div([
        html.Span("STRATEGY", style={'width': '150px', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("SIGNAL", style={'width': '60px', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px', 'text-align': 'center'}),
        html.Span("CONF", style={'width': '80px', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
    ], style={'display': 'flex', 'padding-bottom': '8px', 'border-bottom': f'2px solid {COLORS["border"]}'}))
    watchlist_items = []
    for item in data['watchlist']:
        change_color = COLORS['success'] if item.get('change', 0) >= 0 else COLORS['danger']
        watchlist_items.append(html.Div([
            html.Span(item['symbol'], style={'width': '80px', 'font-weight': 'bold'}),
            html.Span(f"{item['bid']:.5f}", style={'width': '90px', 'text-align': 'right'}),
            html.Span(f"{item['ask']:.5f}", style={'width': '90px', 'text-align': 'right', 'color': COLORS['text_muted']}),
            html.Span(f"{item.get('change', 0):+.2f}%", style={'width': '80px', 'text-align': 'right', 'color': change_color, 'font-weight': 'bold'}),
        ], style={'display': 'flex', 'padding': '6px 5px', 'border-bottom': f'1px solid {COLORS["border"]}', 'align-items': 'center'}))
    watchlist_items.insert(0, html.Div([
        html.Span("SYMBOL", style={'width': '80px', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("BID", style={'width': '90px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("ASK", style={'width': '90px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
        html.Span("CHANGE", style={'width': '80px', 'text-align': 'right', 'font-weight': 'bold', 'color': COLORS['text_muted'], 'font-size': '10px'}),
    ], style={'display': 'flex', 'padding-bottom': '8px', 'border-bottom': f'2px solid {COLORS["border"]}'}))
    equity_fig = create_equity_curve(data['trades_history'])
    pie_fig = create_portfolio_pie(data['positions'])
    return chart_fig, positions_list, signals_list, watchlist_items, equity_fig, pie_fig


def run_terminal(debug=False, port=8050):
    app.run(debug=debug, port=port, host='0.0.0.0')


if __name__ == '__main__':
    run_terminal(debug=True)
