All set! I created a realistic ServiceNow-style dataset and the code you asked for:

### Downloads

* **Dataset (CSV)** – [servicenow\_incidents.csv](sandbox:/mnt/data/servicenow_incidents.csv)
* **Dash dashboard app** – [dash\_app.py](sandbox:/mnt/data/dash_app.py)
* **Jupyter notebook (10 Matplotlib charts)** – [servicenow\_matplotlib\_demo.ipynb](sandbox:/mnt/data/servicenow_matplotlib_demo.ipynb)
* **README** – [README\_SNOW\_DEMO.md](sandbox:/mnt/data/README_SNOW_DEMO.md)

### What’s inside

* **Synthetic incidents (\~1000 rows)** with fields like: `incident_id`, `opened_at`, `resolved_at`, `priority`, `state`, `category`, `subcategory`, `assignment_group`, `assignee`, `channel`, `location`, `configuration_item`, `time_to_first_response_minutes`, `time_to_resolve_minutes`, `reopen_count`, `customer_satisfaction`, `sla_target_minutes`, `sla_breached`.

### Dash dashboard (10 graphs)

Uses pandas for aggregations and Plotly/Dash for visuals (tabs):

1. Incidents by Priority (bar)
2. Incidents Opened per Day (line)
3. Mean Time to Resolve by Priority (bar)
4. SLA Breach % by Assignment Group (bar)
5. Incident State by Category (stacked bar)
6. Opened Hour vs Weekday (heatmap)
7. TTR Distribution by Category (box)
8. Pareto: Top 10 Configuration Items (bar + cumulative %)
9. Workflow Funnel by State (funnel)
10. First Response Time vs CSAT (scatter)

**Run locally**

```bash
pip install pandas dash plotly
python dash_app.py   # open http://127.0.0.1:8050
```

### Jupyter notebook (10 Matplotlib + pandas charts)

The notebook renders these (one figure per cell):

1. Incidents by Priority (bar)
2. Opened per Day (line)
3. Mean TTR by Priority (bar)
4. SLA Breach % by Assignment Group (bar)
5. State by Category (stacked bar)
6. Hour vs Weekday heatmap
7. TTR by Category (boxplot)
8. CI Pareto (bar + cumulative line)
9. Workflow funnel by state (horizontal bar)
10. First response vs CSAT (scatter)

If you want me to tailor the dataset to your actual field names or add extra KPIs (e.g., MTTA/MTTR SLOs, backlog aging), say the word and I’ll regenerate.
