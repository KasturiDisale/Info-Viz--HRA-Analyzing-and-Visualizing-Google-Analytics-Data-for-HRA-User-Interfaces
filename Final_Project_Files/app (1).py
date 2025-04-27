import dash
from dash import dcc, html
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Load the data
df = pd.read_csv(r'S:\Info Viz\Client project\preprocessed_hra_export.csv')


# ----------- Temporal Analysis (Stacked Bar Chart) ------------

# Process event_start
df['event_start'] = pd.to_datetime(df['event_start'], errors='coerce')
df = df.dropna(subset=['event_start', 'event_name'])

# Resample by month
df['event_month'] = df['event_start'].dt.to_period('M').apply(lambda r: r.start_time)
monthly_event_distribution = df.groupby(['event_month', 'event_name']).size().unstack(fill_value=0)
top_events = df['event_name'].value_counts().nlargest(223).index
monthly_event_distribution_top = monthly_event_distribution[top_events]

# Bar chart
custom_colors = {}
for event in top_events:
    if event == 'webpage':
        custom_colors[event] = 'orange'
    else:
        custom_colors[event] = None

fig_temporal = go.Figure()
for event in top_events:
    fig_temporal.add_trace(go.Bar(
        name=event,
        x=[d.strftime('%b %Y') for d in monthly_event_distribution_top.index],
        y=monthly_event_distribution_top[event],
        marker_color=custom_colors[event],
        hovertemplate='<b>Event:</b> %{fullData.name}<br><b>Month:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>'
    ))

fig_temporal.update_layout(
    barmode='stack',
    title='Temporal Analysis: User Events Distribution Over Time (Monthly)',
    title_x=0.5,
    xaxis_title='Month',
    yaxis_title='Number of Events',
    legend_title='Event Name',
    xaxis_tickangle=-90,
    width=1000,
    height=800,
    margin=dict(l=40, r=40, t=80, b=80),
    font=dict(size=12),
    legend=dict(
        yanchor="top",
        y=1,
        xanchor="left",
        x=1.02,
        font=dict(size=8),
        itemwidth=30
    )
)

# ----------- Spatial Analysis (Heatmap) ------------

# Prepare dataset for heatmap
df_filtered = df[(df['event_category'] != 'mousemove') & (df['event_category'].notna())]
df_filtered['event_timestamp'] = pd.to_datetime(df_filtered['event_timestamp'], unit='ms', errors='coerce')
df_filtered['time_bucket'] = df_filtered['event_timestamp'].dt.floor('5min')
df_filtered['pseudo_session'] = (
    df_filtered['user_pseudo_id'].astype(str) + '_' +
    df_filtered['page_location'].astype(str) + '_' +
    df_filtered['time_bucket'].astype(str)
)

top_categories = df_filtered['event_category'].value_counts().nlargest(30).index.tolist()
df_top = df_filtered[df_filtered['event_category'].isin(top_categories)]
pivot_matrix_top = pd.crosstab(df_top['pseudo_session'], df_top['event_category'])
correlation_matrix_top = pivot_matrix_top.corr()

# Heatmap
fig_spatial = px.imshow(
    correlation_matrix_top,
    text_auto=".2f",
    color_continuous_scale='OrRd',
    labels=dict(color="Correlation")
)

fig_spatial.update_layout(
    title='Spatial Analysis: Correlation Heatmap of UI Elements',
    title_x=0.5,
    width=1000,
    height=800,
    margin=dict(l=10, r=10, t=80, b=80),
    xaxis_side="bottom",
    font=dict(size=12),
    coloraxis_colorbar=dict(
        x=0.88,
        thickness=15,
        len=0.8,
        title_side='top'
    )
)

# ----------- Network Analysis (Sankey Diagram) ------------

# Sankey (as you want exactly)
df = df.sort_values(by=['user_pseudo_id', 'event_timestamp'])
df['next_event'] = df.groupby('user_pseudo_id')['event_name'].shift(-1)
transition_counts = df.groupby(['event_name', 'next_event']).size().reset_index(name='weight')
top_links = transition_counts.sort_values(by='weight', ascending=False).head(223)

labels = pd.unique(top_links[['event_name', 'next_event']].values.ravel())
label_to_index = {label: i for i, label in enumerate(labels)}

sources = top_links['event_name'].map(label_to_index)
targets = top_links['next_event'].map(label_to_index)
values = top_links['weight']

color_palette = px.colors.qualitative.Plotly
node_colors = [color_palette[i % len(color_palette)] for i in range(len(labels))]
for i, label in enumerate(labels):
    if label == 'webpage':
        node_colors[i] = 'orange'

link_colors = [node_colors[src] for src in sources]

fig_network = go.Figure(data=[go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=labels,
        color=node_colors
    ),
    link=dict(
        source=sources,
        target=targets,
        value=values,
        color=link_colors
    )
)])

fig_network.update_layout(
    title_text="Network Analysis: User Event Flow",
    title_x=0.5,
    font_size=12,
    height=1000,
    width=2400
)

# ----------- Dash App Layout ------------

# App initialization
app = dash.Dash(__name__)

# Border style
card_style = {
    'border': '2px solid #cccccc',
    'border-radius': '10px',
    'padding': '20px',
    'box-shadow': '2px 2px 8px lightgrey',
    'background-color': '#ffffff',
    'margin': '10px'
}

# Layout
app.layout = html.Div([
    html.H1("HRA : UI User Analytics Dashboard", style={'textAlign': 'center'}),
    html.Hr(),

    html.Div([
        html.Div([
            html.H2("Temporal Analysis: User Events Distribution Over Time (Monthly)", style={'textAlign': 'center'}),
            dcc.Graph(figure=fig_temporal)
        ], style={**card_style, 'width': '50%', 'display': 'inline-block'}),

        html.Div([
            html.H2("Spatial Analysis: Correlation Heatmap of UI Elements", style={'textAlign': 'center'}),
            dcc.Graph(figure=fig_spatial)
        ], style={**card_style, 'width': '50%', 'display': 'inline-block'}),
    ], style={'display': 'flex', 'justify-content': 'space-around'}),

    html.Br(),

    html.Div([
        html.H2("Network Analysis: User Event Flow", style={'textAlign': 'center'}),
        dcc.Graph(figure=fig_network)
    ], style={**card_style, 'width': '98%', 'margin': 'auto'})
])

if __name__ == '__main__':
    app.run(debug=True)
