
# ServiceNow Synthetic Dataset + Visualizations

This package contains:
- `servicenow_incidents.csv` ‚Äî Synthetic dataset with 1000 incidents.
- `dash_app.py` ‚Äî Dash dashboard with 10 interactive charts (uses pandas for prep).
- `servicenow_matplotlib_demo.ipynb` ‚Äî Jupyter notebook with 10 matplotlib charts.

## Run the Dash app
```bash
pip install pandas dash plotly
python dash_app.py  # then open http://127.0.0.1:8050
```

## Open the notebook
Install Jupyter if needed, then open the notebook and run all cells.

## Fields
Key columns include: incident_id, opened_at, resolved_at, priority, state, category, subcategory,
assignment_group, assignee, channel, location, configuration_item, time_to_first_response_minutes,
time_to_resolve_minutes, reopen_count, customer_satisfaction, sla_target_minutes, sla_breached.

![Uploading image.png…]()
