import pandas as pd
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import datetime
import plotly.express as px
import geopandas as gpd
import io
import base64
import matplotlib.pyplot as plt
from shapely.wkt import loads

# Load the data
df = pd.read_pickle("HWH-KOL_combined.pickle")
df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')

# Convert the 'geometry' column to Shapely geometries
df['geometry'] = df['geometry'].apply(loads)

# Create a GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry='geometry')


def generate_plot(filtered_gdf):
    fig_map = px.choropleth_mapbox(
        filtered_gdf,
        geojson=filtered_gdf.geometry.__geo_interface__,
        locations=filtered_gdf.index,
        color='PM2.5',
        color_continuous_scale="jet",
        color_continuous_midpoint=70,
        range_color=[20, 120],  # Fixed color scale range
        mapbox_style="open-street-map",
        zoom=10.6,
        center={"lat": filtered_gdf.geometry.centroid.y.mean(), "lon": filtered_gdf.geometry.centroid.x.mean()},
        opacity=0.8,
        labels={'color': 'PM2.5'},
    )

    fig_map.update_traces(
        customdata=filtered_gdf[['WARD', 'Area', 'PM2.5']],
        hovertemplate='<b>Ward:</b> %{customdata[0]}<br><b>Area:</b> %{customdata[1]}<br><b>PM2.5:</b> %{customdata[2]:.2f}'
    )

    fig_map.update_layout(coloraxis_showscale=False)
    fig_map.update_layout(margin={"r": 5, "t": 5, "l": 10, "b": 0})

    return fig_map


# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Generate marks for each month
month_marks = {i: (datetime.date(2023, 1, 1) + datetime.timedelta(days=i - 1)).strftime('%b %d') for i in range(1, 365)}

# Filter the marks to include only the first day of each month
unique_month_marks = {key: value.split()[0] for key, value in month_marks.items() if value.endswith(' 01')}

# Define the Dash app layout
app.layout = html.Div([
    html.Div([
        html.Img(src="/assets/image.png", style={'height': '60px', 'width': '100px'}),
        html.H1("Dashboard for Ward Level PM 2.5 Prediction for Howrah and Kolkata", style={'text-align': 'center'}),
        html.Img(src="/assets/favicon.ico", style={'height': '100px', 'width': '100px'})
    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),

    html.Div([
        html.Label("Select City:", style={'font-weight': 'bold'}),
        dcc.Dropdown(
            id='city-dropdown',
            options=[
                {'label': city, 'value': city} for city in gdf['City'].unique()
            ],
            value=gdf['City'].iloc[0],  # Default selected city
            style={'width': '50%'}  # Adjust the width and margin as needed
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),  # Adjust margin as needed

    html.Div([
        dcc.Graph(
            id='transparent-box',
            style={'height': '500px', 'width': '92%', 'display': 'inline-block', 'margin': '0px',
                   'vertical-align': 'top'}),

        html.Img(
            id='colorbar-image',
            src='',  # Set to the colorbar image source
            style={'height': '500px', 'width': '8%', 'display': 'inline-block', 'margin': '0px',
                   'vertical-align': 'top'}
        )
    ], style={'text-align': 'center', 'margin': '0px'}),  # Set margin to zero

    html.Div([
        html.Label("Selected Date:"),
        html.Div(id='selected-date-output', style={'text-align': 'center'}),
        dcc.Slider(
            id='day-slider',
            min=1,
            max=365,
            step=1,
            marks=unique_month_marks,
            value=1,  # Default value for the middle of the year
            tooltip={'placement': 'bottom', 'always_visible': True, 'format': 'MMM DD YYYY'}
            # Show full date in tooltip
        ),
    ], style={'text-align': 'center', 'margin': '0px'}),  # Set margin to zero

    html.Div([
        html.P("Created and Maintained by IIT Delhi Team", style={'text-align': 'right', 'font-size': '10px'})
    ], style={'background-color': '#f0f0f0'}),
])  # Additional overall margin set to zero


@app.callback(
    [Output('transparent-box', 'figure'),
     Output('colorbar-image', 'src'),
     Output('selected-date-output', 'children')],
    [Input('city-dropdown', 'value'),
     Input('day-slider', 'value')]
)
def update_graph(selected_city, selected_day):
    filtered_data = gdf[(gdf['City'] == selected_city) & (gdf['Date'].dt.dayofyear == selected_day)]

    fig = generate_plot(filtered_data)

    fig_colorbar, ax_colorbar = plt.subplots(figsize=(10, 6), dpi=1200)  # Adjust the figsize and dpi as needed
    cmap = plt.cm.get_cmap('jet')
    norm = plt.Normalize(vmin=20, vmax=120)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])

    ax_colorbar.set_visible(False)

    cb = plt.colorbar(sm, ax=ax_colorbar, extend='both', label='PM 2.5(µg/m3)', orientation='vertical')

    colorbar_img = io.BytesIO()
    fig_colorbar.savefig(colorbar_img, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig_colorbar)

    colorbar_img_str = f"data:image/png;base64,{base64.b64encode(colorbar_img.getvalue()).decode()}"

    selected_date = (datetime.date(2023, 1, 1) + datetime.timedelta(days=selected_day - 1)).strftime('%b %d, %Y')

    return {'data': fig.data, 'layout': fig.layout}, colorbar_img_str, f"{selected_date}"


if __name__ == '__main__':
    app.run_server(debug=False)
