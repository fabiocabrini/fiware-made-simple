#!/usr/bin/env python3
"""Web dashboard for the STH-Comet history (Dash + Plotly).

Queries STH-Comet periodically and plots the series with its mean.

Usage:
    python dashboard.py --host SERVER_IP
    python dashboard.py --host SERVER_IP --entity-id urn:ngsi-ld:Lamp:002 --attribute luminosity

Then open http://localhost:8050 in your browser.
"""
import argparse
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import dash
import plotly.graph_objs as go
import requests
from dash import dcc, html, no_update
from dash.dependencies import Input, Output, State


def parse_args():
    p = argparse.ArgumentParser(description="STH-Comet history dashboard")
    p.add_argument("--host", default=os.getenv("FIWARE_HOST"), help="IP address or name of the FIWARE server (or FIWARE_HOST)")
    p.add_argument("--service", default="smart", help="fiware-service")
    p.add_argument("--servicepath", default="/", help="fiware-servicepath")
    p.add_argument("--entity-type", default="Lamp")
    p.add_argument("--entity-id", default="urn:ngsi-ld:Lamp:001")
    p.add_argument("--attribute", default="luminosity")
    p.add_argument("--last-n", type=int, default=30, help="values requested from STH-Comet on each refresh (max 100)")
    p.add_argument("--max-points", type=int, default=200, help="points kept in the chart")
    p.add_argument("--interval", type=float, default=3, help="seconds between refreshes")
    p.add_argument("--tz", help="display time zone, e.g. America/New_York (default: this computer's time zone)")
    p.add_argument("--port", type=int, default=8050, help="dashboard port")
    args = p.parse_args()
    if not args.host:
        p.error("set the server with --host or with the FIWARE_HOST variable")
    return args


def fetch_history(args):
    """Returns the list of values from STH-Comet ({recvTime, attrValue, ...})."""
    url = (f"http://{args.host}:8666/STH/v1/contextEntities/type/{args.entity_type}"
           f"/id/{args.entity_id}/attributes/{args.attribute}")
    headers = {"fiware-service": args.service, "fiware-servicepath": args.servicepath}
    try:
        response = requests.get(url, headers=headers, params={"lastN": args.last_n}, timeout=5)
        response.raise_for_status()
        return response.json()["contextResponses"][0]["contextElement"]["attributes"][0]["values"]
    except (requests.RequestException, KeyError, IndexError, ValueError) as error:
        print(f"Error querying STH-Comet: {error}")
        return []


def create_app(args):
    tz = ZoneInfo(args.tz) if args.tz else None  # None = local time zone
    tz_label = args.tz or "local time"
    app = dash.Dash(__name__, title="FIWARE Made Simple")
    app.layout = html.Div(
        style={"fontFamily": "Helvetica, Arial, sans-serif", "maxWidth": "1100px", "margin": "0 auto"},
        children=[
            html.H2(f"{args.attribute} · {args.entity_id}"),
            dcc.Graph(id="chart"),
            # {recvTime (UTC): value}: avoids duplicated points between refreshes
            dcc.Store(id="data", data={}),
            dcc.Interval(id="clock", interval=args.interval * 1000, n_intervals=0),
        ],
    )

    @app.callback(Output("data", "data"), Input("clock", "n_intervals"), State("data", "data"))
    def update_data(_, data):
        new_values = fetch_history(args)
        if not new_values:
            return no_update
        for item in new_values:
            try:
                data[item["recvTime"]] = float(item["attrValue"])
            except (KeyError, TypeError, ValueError):
                continue
        return dict(sorted(data.items())[-args.max_points:])

    @app.callback(Output("chart", "figure"), Input("data", "data"))
    def draw(data):
        if not data:
            return go.Figure(layout={"title": "Waiting for data from STH-Comet..."})
        points = sorted(data.items())
        times = [datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(tz) for t, _ in points]
        values = [v for _, v in points]
        mean = sum(values) / len(values)

        figure = go.Figure([
            go.Scatter(x=times, y=values, mode="lines+markers", name=args.attribute,
                       line={"color": "#ea580c"}),
            go.Scatter(x=[times[0], times[-1]], y=[mean, mean], mode="lines",
                       name=f"mean ({mean:.1f})", line={"color": "#2563eb", "dash": "dash"}),
        ])
        figure.update_layout(
            title=f"Latest value: {values[-1]:g}",
            xaxis_title=f"Time ({tz_label})",
            yaxis_title=args.attribute,
            hovermode="x unified",
            uirevision="keep",  # keeps zoom and pan between refreshes
        )
        return figure

    return app


if __name__ == "__main__":
    args = parse_args()
    create_app(args).run(host="0.0.0.0", port=args.port, debug=False)
