from __future__ import annotations
import plotly.express as px
import plotly.graph_objects as go

# Consistent color maps used across pages
RISK_COLORS = {
    "Normal": "#2ca02c",
    "Watch": "#ff7f0e",
    "Critical": "#d62728",
    "Span Jacking Likely": "#d62728",
}

CONFIDENCE_COLORS = {
    "High": "#2ca02c",
    "Medium": "#1f77b4",
    "Low": "#ff7f0e",
    "Poor": "#d62728",
    "Insufficient Data": "#7f7f7f",
}

_LAYOUT_BASE = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=13),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=60, r=40, t=60, b=50),
    hovermode="closest",
)

_AXIS_STYLE = dict(showgrid=True, gridcolor="#eeeeee", linecolor="#cccccc", linewidth=1)


def apply_plot_layout(fig, title=None, xaxis_title=None, yaxis_title=None):
    """Apply consistent layout defaults to any Plotly figure."""
    updates = dict(**_LAYOUT_BASE)
    if title:
        updates["title"] = title
    fig.update_layout(**updates)
    x_upd = dict(**_AXIS_STYLE)
    y_upd = dict(**_AXIS_STYLE)
    if xaxis_title:
        x_upd["title"] = xaxis_title
    if yaxis_title:
        y_upd["title"] = yaxis_title
    fig.update_xaxes(**x_upd)
    fig.update_yaxes(**y_upd)
    return fig


def river_stage_plot(river_df, events_df=None, possible_threshold=12, likely_threshold=7):
    fig = px.line(
        river_df,
        x="timestamp",
        y="stage_ft",
        labels={"timestamp": "Date", "stage_ft": "River Stage (ft)"},
        title="River Stage Time History",
        color_discrete_sequence=["#1f77b4"],
    )
    fig.add_hline(
        y=possible_threshold,
        line_dash="dash",
        line_color="#ff7f0e",
        annotation_text=f"{possible_threshold:.0f} ft — movement possible",
        annotation_font_color="#ff7f0e",
    )
    fig.add_hline(
        y=likely_threshold,
        line_dash="dash",
        line_color="#d62728",
        annotation_text=f"{likely_threshold:.0f} ft — movement likely",
        annotation_font_color="#d62728",
    )
    if events_df is not None and not events_df.empty:
        for _, ev in events_df.iterrows():
            fig.add_vrect(x0=ev["start_date"], x1=ev["end_date"], opacity=0.12, line_width=0)
    apply_plot_layout(fig, xaxis_title="Date", yaxis_title="River Stage (ft)")
    fig.update_layout(height=520)
    return fig


def time_series_plot(df, x, y, color=None, title=""):
    return px.line(df, x=x, y=y, color=color, title=title)
