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
    timestampDiffsFromStart = [element - jsonPayload['timestamp'][0] for element in jsonPayload['timestamp']]

    # Pulling out the timestamp count for ease
    timestampCount = len(timestampDiffsFromStart)
    
    # Flattening the general data from the json
    def flatten_dict(d: MutableMapping, sep: str= '/') -> MutableMapping:
        [flat_dict] = pd.json_normalize(d, sep=sep).to_dict(orient='records')
        return flat_dict

    flatData = flatten_dict(jsonPayload)

    attrs = []

    headings = []
    for key in flatData:
        if isinstance(flatData[key], list): 
            if key != 'timestamp':
                headings.append(key)
        else:
            attrs.append(key)
    
    superHeadingGroup = {}
    for heading in headings:
        superHeadingSplit = str(heading).split('/')
        superHeading = superHeadingSplit[0]
        subHeading = superHeadingSplit[1]
        if superHeading not in dict.keys(superHeadingGroup):
            superHeadingGroup[superHeading] = {}
        superHeadingGroup[superHeading][subHeading] = dict.get(flatData, heading)
        superHeadingGroup[superHeading] = {key:superHeadingGroup[superHeading][key] for key in sorted(superHeadingGroup[superHeading].keys())}
    plots = []
    
    for superHeading in superHeadingGroup:
        subGroups = {}
        supe = dict.get(superHeadingGroup, superHeading)
        for subKey in supe:
            sub = dict.get(supe, subKey)
            subGroups[subKey] = sub
        
        # fig = go.Figure(layout={'title': superHeading})
        colors = ['red', 'blue', 'blue', 'blue']
        scatter = px.scatter(title=superHeading)
        for group in subGroups:
            subGroup = dict.get(subGroups, group)
            if not None in subGroup:
                scatter.add_scatter(x=timestampDiffsFromStart, y=subGroup, name=group)
                # fig.add_trace(go.Scatter(x=timestampDiffsFromStart, y=subGroup, mode='lines', name=group))

        plots.append(html.Div([
                    # dcc.Graph(figure=fig, id={'type': 'plot', 'index': heading})
                    dcc.Graph(figure=scatter, id={'type': 'plot', 'index': heading})
                ]))
    return [getAttributes(flatData, attrs), plots]

# Initialize the app and generate the plots for all valid data segments (where the entry count is the same as the timestamp count)
def initApp():
    app = dash.Dash(__name__)
    app.layout = html.Div([
        html.H1("JSON Plotting Tool"),
        html.Div([
            dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Files')
            ]),
            style={
                'width': '30%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=False
        ),
        html.Div(id='output-data-upload'),
        ]),
        html.Div(id='attrs-container', children=[]),
        html.Div(id='plot-container', children=[]),
    ])
    
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
    
    if(len(keys) > 0 and len(values) > 0):
        df = pd.DataFrame({'key': keys, 'value': values})
        return html.Div(className="table", children=[dash_table.DataTable(df.to_dict('records'), [{"name": i, "id": i} for i in df.columns], style_cell={'textAlign': 'center'},)], style={'width': '50%'})
    else:
        return []

app = initApp()
app.run_server(debug=True)