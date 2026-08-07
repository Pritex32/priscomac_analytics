import plotly.graph_objects as go
import plotly.utils
import json
from typing import Dict, Any

def build_forecast_chart(original: pd.DataFrame, forecast: pd.DataFrame) -> Dict[str, Any]:
    fig = go.Figure()

    ts = original.groupby("date")["demand"].sum().reset_index()

    fig.add_trace(go.Scatter(
        x=ts["date"], y=ts["demand"],
        mode="lines", name="Historical",
        line=dict(color="#D32F2F", width=2)
    ))

    fig.add_trace(go.Scatter(
        x=forecast["date"], y=forecast["predicted"],
        mode="lines", name="Forecast",
        line=dict(color="#1976D2", width=2, dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=forecast["date"], y=forecast["upper"],
        mode="lines", name="Upper Bound",
        line=dict(width=0), showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=forecast["date"], y=forecast["lower"],
        mode="lines", name="Lower Bound",
        line=dict(width=0),
        fillcolor="rgba(25, 118, 210, 0.1)",
        fill="tonexty", showlegend=False
    ))

    fig.update_layout(
        title="Demand Forecast",
        xaxis_title="Date",
        yaxis_title="Demand",
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    return json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))

def build_summary_chart(summary: dict) -> Dict[str, Any]:
    labels = ["Avg Demand", "Max Demand", "Min Demand"]
    values = [summary["avg_demand"], summary["max_demand"], summary["min_demand"]]

    fig = go.Figure([go.Bar(x=labels, y=values, marker_color="#D32F2F")])
    fig.update_layout(
        title="Summary Statistics",
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return json.loads(plotly.utils.PlotlyJSONEncoder().encode(fig))
