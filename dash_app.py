
import pandas as pd
from datetime import datetime
from dash import Dash, dcc, html
import plotly.express as px
import plotly.graph_objects as go

df = pd.read_csv("servicenow_incidents.csv", parse_dates=["opened_at","resolved_at"])

app = Dash(__name__)
app.title = "ServiceNow Ops Dashboard"

df["opened_date"] = df["opened_at"].dt.date
df["opened_week"] = df["opened_at"].dt.to_period("W").astype(str)
df["opened_hour"] = df["opened_at"].dt.hour
df["opened_wday"] = df["opened_at"].dt.day_name()

g1 = df["priority"].value_counts().reset_index().rename(columns={"index":"priority","priority":"count"})
fig1 = px.bar(g1, x="priority", y="count", title="Incidents by Priority")

g2 = df.groupby("opened_date").size().reset_index(name="count")
fig2 = px.line(g2, x="opened_date", y="count", title="Incidents Opened per Day")

g3 = df.dropna(subset=["time_to_resolve_minutes"]).groupby("priority")["time_to_resolve_minutes"].mean().reset_index()
fig3 = px.bar(g3, x="priority", y="time_to_resolve_minutes", title="Mean TTR by Priority")

g4 = df.groupby("assignment_group")["sla_breached"].mean().reset_index()
g4["sla_breach_pct"] = (g4["sla_breached"] * 100).round(2)
fig4 = px.bar(g4.sort_values("sla_breach_pct", ascending=False).head(10),
              x="assignment_group", y="sla_breach_pct",
              title="Top 10 Assignment Groups by SLA Breach %")

g5 = df.pivot_table(index="category", columns="state", values="incident_id", aggfunc="count", fill_value=0).reset_index()
fig5 = px.bar(g5, x="category", y=g5.columns[1:], title="Incident States by Category", barmode="stack")

g6 = df.pivot_table(index="opened_wday", columns="opened_hour", values="incident_id", aggfunc="count", fill_value=0)
g6 = g6.reindex(["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
fig6 = px.imshow(g6, aspect="auto", title="Incidents Opened: Hour vs Weekday")

g7 = df.dropna(subset=["time_to_resolve_minutes"])
fig7 = px.box(g7, x="category", y="time_to_resolve_minutes", title="TTR Distribution by Category")

g8 = df["configuration_item"].value_counts().head(10).reset_index()
g8.columns = ["configuration_item","count"]
g8["cum_pct"] = g8["count"].cumsum() / g8["count"].sum() * 100
fig8 = go.Figure()
fig8.add_bar(x=g8["configuration_item"], y=g8["count"], name="Count")
fig8.add_trace(go.Scatter(x=g8["configuration_item"], y=g8["cum_pct"], yaxis="y2", name="Cumulative %"))
fig8.update_layout(title="Pareto: Top 10 Configuration Items",
                   yaxis2=dict(overlaying='y', side='right', range=[0,100], title="Cumulative %"))

g9 = df["state"].value_counts()[["New","In Progress","On Hold","Resolved","Closed","Cancelled"]].fillna(0).reset_index()
g9.columns = ["state","count"]
fig9 = px.funnel(g9, x="count", y="state", title="Workflow Funnel by State")

g10 = df.dropna(subset=["customer_satisfaction"])
fig10 = px.scatter(g10, x="time_to_first_response_minutes", y="customer_satisfaction",
                   title="First Response Time vs CSAT", trendline=None)

app.layout = html.Div([
    html.H1("ServiceNow Operational Dashboard"),
    html.P("Synthetic demo dataset. Use this to explore KPI trends and drilldowns."),
    dcc.Tabs([
        dcc.Tab(label="Priority Mix", children=[dcc.Graph(figure=fig1)]),
        dcc.Tab(label="Daily Volume", children=[dcc.Graph(figure=fig2)]),
        dcc.Tab(label="TTR by Priority", children=[dcc.Graph(figure=fig3)]),
        dcc.Tab(label="SLA Breach %", children=[dcc.Graph(figure=fig4)]),
        dcc.Tab(label="State by Category", children=[dcc.Graph(figure=fig5)]),
        dcc.Tab(label="Hourly Heatmap", children=[dcc.Graph(figure=fig6)]),
        dcc.Tab(label="TTR by Category", children=[dcc.Graph(figure=fig7)]),
        dcc.Tab(label="CI Pareto", children=[dcc.Graph(figure=fig8)]),
        dcc.Tab(label="State Funnel", children=[dcc.Graph(figure=fig9)]),
        dcc.Tab(label="First Response vs CSAT", children=[dcc.Graph(figure=fig10)]),
    ])
])

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
