import base64
import json
from typing import MutableMapping
import pandas as pd
import dash
from dash import dcc
from dash import html
from dash import dash_table
import plotly.graph_objects as go
import plotly.express as px

def parseData(jsonPayload):
    # Building the time series for the X axis
    timestampDiffsFromStart = [element - jsonPayload['timestamp'][0] for element in jsonPayload['timestamp']]
    
    # Flattening the general data from the json
    def flatten_dict(d: MutableMapping, sep: str= '/') -> MutableMapping:
        [flat_dict] = pd.json_normalize(d, sep=sep).to_dict(orient='records')
        return flat_dict

    flatData = flatten_dict(jsonPayload)
    
    # This will populate the table at the top of the page with one-off attributes
    attrs = []
    
    # Build the main heading/data-point key list.  This is less useful now that datasets aren't excluded if they don't have the exact number of steps as the X axis
    headings = []
    for key in flatData:
        if isinstance(flatData[key], list): 
            if key != 'timestamp':
                headings.append(key)
        else:
            attrs.append(key)
    
    # We break out the sub heading, HV/TV1 etc, from the super heading, ie headway_second, and collect them in a dict for each super heading
    superHeadingGroup = {}
    for heading in headings:
        superHeadingSplit = str(heading).split('/')
        superHeading = superHeadingSplit[0]
        subHeading = superHeadingSplit[1]
        if superHeading not in dict.keys(superHeadingGroup):
            superHeadingGroup[superHeading] = {}
        superHeadingGroup[superHeading][subHeading] = dict.get(flatData, heading)
        # We alpha sort the subheadings so HV will always be the first element plotted
        superHeadingGroup[superHeading] = {key:superHeadingGroup[superHeading][key] for key in sorted(superHeadingGroup[superHeading].keys())}
    
    # We build the plot collection
    plots = []
    for superHeading in superHeadingGroup:
        subGroups = {}
        supe = dict.get(superHeadingGroup, superHeading)
        for subKey in supe:
            sub = dict.get(supe, subKey)
            subGroups[subKey] = sub
        
        # We add an empty plotly express scatter plot, and title it
        scatter = px.scatter(title=superHeading)
        for group in subGroups:
            subGroup = dict.get(subGroups, group)
            # Some datasets contain null values which don't marshal well in python (zeroes would be better, or omitted entirely), they're excluded here
            if not None in subGroup:
                # Color HVs red, everything else a partially transparent blue
                color = 'red'
                if 'HV' not in group:
                    color = 'rgba(111, 140, 209, 0.5)'
                # Add the subplot and line style
                scatter.add_scatter(x=timestampDiffsFromStart, y=subGroup, name=group, line={'color':color})
        
        # Add the super plot to the plots collection
        plots.append(html.Div([
                    dcc.Graph(figure=scatter, id={'type': 'plot', 'index': heading})
                ]))
    # Build out the attributes table, return the product and the plots collection for rendering
    return [getAttributes(flatData, attrs), plots]

# Initialize the app and generate the plots for all valid data segments (where the entry count is the same as the timestamp count)
def initApp():
    app = dash.Dash(__name__)
    app.layout = html.Div([
        html.Div([
            html.H1("JSON Plotting Tool"), 
            html.Div([
                html.Div([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            html.A('Select File')
                        ]),
                        style={
                            'display': 'flex', 
                            'flex-direction': 'column', 
                            'justify-content': 'center',
                            'width': '150px',
                            'height': '30px',
                            'borderWidth': '1px',
                            'borderStyle': 'solid',
                            'borderRadius': '3px',
                            'textAlign': 'center',
                        },
                        multiple=False
                    ),
                    html.Div(id='output-data-upload'),
                    html.Button('Generate Report', id='report', style={
                    'width': '150px',
                    'height': '30px',
                    'borderWidth': '1px',
                    'borderRadius': '3px',
                    'textAlign': 'center',
                    'margin': '10px'
                }),
            ], style={'display': 'flex', 'flex-direction': 'row', 'justify-content': 'center', 'justify-items': 'center', 'align-content': 'center', 'align-items': 'center'}),
        ]),], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center', 'justify-items': 'center', 'align-content': 'center', 'align-items': 'center'}),
        html.Div(id='attrs-container', children=[]),
        html.Div(id='plot-container', children=[], style={'display': 'flex', 'flex-flow': 'row wrap', 'justify-content': 'center', 'justify-items': 'center', 'align-content': 'center', 'align-items': 'center'}),
    ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center', 'justify-items': 'center', 'align-content': 'center', 'align-items': 'center'})
    
    # Whenever a new file is selected for plotting, return new data, or safe empty data
    @app.callback(dash.dependencies.Output('attrs-container', 'children'),
                dash.dependencies.Output('plot-container', 'children'),
              dash.dependencies.Input('upload-data', 'contents'),
              dash.dependencies.State('upload-data', 'filename'),
              )
    def selectFile(contents, filename):
        if contents is not None:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string).decode('ascii')
            [attrs, plots] = parseData(json.loads(decoded))
            return [attrs, plots]
        else:
            return [[],[]]

    return app

def getAttributes(flatData, attrs):
    keys = []
    values = []
    for attr in attrs:
        if "/" in attr:
            label = str(attr).split("/")[1]
        else:
            label = str(attr)
        keys.append(label)
        values.append(str(dict.get(flatData,attr)))
    
    # Build a basic table from a Dataframe containing key/values of one-off values from the dataset
    if(len(keys) > 0 and len(values) > 0):
        df = pd.DataFrame({'key': keys, 'value': values})
        return html.Div(className="table", children=[dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], style_cell={'textAlign': 'center'},)], style={'width': '50%'})
    else:
        return []

app = initApp()
app.run_server(debug=True)