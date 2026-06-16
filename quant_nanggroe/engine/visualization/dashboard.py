class QNADashboard:
    def __init__(self, title: str = "Quant-Nanggroe-AI Dashboard"):
        self.title = title
        self._pages = []

    def add_page(self, name: str, layout_fn):
        self._pages.append({"name": name, "layout": layout_fn})

    def run_server(self, host: str = "0.0.0.0", port: int = 8050):
        try:
            import dash
            from dash import dcc, html

            app = dash.Dash(__name__)
            app.title = self.title
            app.layout = html.Div([
                html.H1(self.title),
                dcc.Tabs([
                    dcc.Tab(label=p["name"], children=[p["layout"]()])
                    for p in self._pages
                ]),
            ])
            app.run_server(host=host, port=port, debug=False)
        except ImportError:
            print("dash not installed. Install with: pip install dash")
