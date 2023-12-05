import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pm4py
# from pm4py.objects.log.importer.xes import importer as xes_importer
# from pm4py.objects.log.importer.csv import importer as csv_importer
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
# from pm4py.visualization.bpmn import importer as bpmn_visualization
import plotly.express as px
import pandas as pd
import base64
import io
import graphviz
import os
from PIL import Image
import re


os.environ['PATH'] += os.pathsep + 'C:/Program Files/Graphviz/bin'
# Function to read XES file
def read_xes(file_path):
    log = pm4py.read_xes(file_path)
    # log = xes_importer.apply(file_path)
    return log

# Function to read CSV file
def read_csv(file_path, case_id_col, activity_col, timestamp_col):
    dataframe = pd.read_csv(file_path, sep=',')
    dataframe = pm4py.format_dataframe(dataframe, case_id=case_id_col, activity_key=activity_col, timestamp_key=timestamp_col)
    event_log = pm4py.convert_to_event_log(dataframe)
    # log = csv_importer.apply(file_path, parameters={"case_id": case_id_col, "activity": activity_col, "time": timestamp_col})
    return event_log

# Initialize the app
app = dash.Dash(__name__)

# Define the layout of the app
app.layout = html.Div([
    html.H1("Process Mining App"),

    dcc.Upload(
        id='upload-data',
        children=html.Button('Upload File'),
        multiple=False
    ),

    html.Div([
        html.Label('Case ID Column'),
        dcc.Dropdown(id='case-id-dropdown'),

        html.Label('Activity Column'),
        dcc.Dropdown(id='activity-dropdown'),

        html.Label('Timestamp Column'),
        dcc.Dropdown(id='timestamp-dropdown'),
    ]),

    # html.Div([
    # html.Label('Update Model'),
    # dcc.Checklist(
    #     id='update-checklist',
    #     options=[
    #         {'label': 'Update Model', 'value': 'update'},
    #         # Add more options as needed
    #     ],
    #     value=[],
    # ),
    # ]),

    #new
    html.Div([
        html.Label('Update Model'),
        dcc.RadioItems(
            id='update-checklist',
            options=[
                {'label': 'BPMN', 'value': 'update_bpmn'},
                {'label': 'Filtering', 'value': 'filtering'},
                {'label': 'Petri Net', 'value': 'petri'},
                # Add more algorithms if needed
            ],
            value= 'update_bpmn'
        ),
    ]),


    html.Div([
        html.Label('Filter Parameters'),
        dcc.RangeSlider(
            id='filter-slider',
            min=0,
            max=100,
            step=1,
            marks={i: str(i) for i in range(0, 101)},
            value=[0, 100]
        ),
    ]),

    html.Div([
        html.Label('Mining Algorithm'),
        dcc.RadioItems(
            id='algorithm-radio',
            options=[
                {'label': 'Inductive Miner', 'value': 'inductive_miner'},
                {'label': 'Our solution', 'value': 'our_sol'},
                # Add more algorithms if needed
            ],
            value='inductive_miner'
        ),
    ]),
    html.Div(id='bpmn-container')
    # dcc.Graph(id='bpmn-graph'),
])

# Callback to update dropdowns based on file type
@app.callback(
    [Output('case-id-dropdown', 'options'),
     Output('case-id-dropdown', 'value'),
     Output('activity-dropdown', 'options'),
     Output('activity-dropdown', 'value'),
     Output('timestamp-dropdown', 'options'),
     Output('timestamp-dropdown', 'value')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_dropdowns(contents, filename):
    if contents is not None:
        print('weszło')
        file_extension = contents.split('.')[-1]
        if 'xes' in filename:
            return [], [], [], [], [], []
        elif 'csv' in filename:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string).decode('utf-8')
            df = pd.read_csv(io.StringIO(decoded))
            columns = [{'label': col, 'value': col} for col in df.columns]
            print(columns)
            regex_pattern = re.compile(r'(case|id)', flags=re.IGNORECASE)
            case_id = [col['value'] for col in columns if re.search(regex_pattern, col['value'])]
            if len(case_id) > 0:
                case_id = case_id[0]
            regex_pattern = re.compile(r'(activity)', flags=re.IGNORECASE)
            activity = [col['value'] for col in columns if re.search(regex_pattern, col['value'])]
            if len(activity) > 0:
                activity = activity[0]
            regex_pattern = re.compile(r'(time|date)', flags=re.IGNORECASE)
            time = [col['value'] for col in columns if re.search(regex_pattern, col['value'])]
            if len(time) > 0:
                time = time[0]
            return columns,case_id, columns,activity, columns,time
    return [], [], [], [], [], []

# Callback to update BPMN graph based on user inputs
@app.callback(
    Output('bpmn-container', 'children'),
    [Input('upload-data', 'contents'),
     Input('case-id-dropdown', 'value'),
     Input('activity-dropdown', 'value'),
     Input('timestamp-dropdown', 'value'),
     Input('filter-slider', 'value'),
     Input('algorithm-radio', 'value'),
     Input('update-checklist', 'value')],
     State('upload-data', 'filename')
)
def update(contents, case_id_col, activity_col, timestamp_col, filter_range, algorithm, update_checkbox,filename):
    if contents is not None and update_checkbox == 'update_bpmn':
        content_type, content_string = contents.split(',')
        # print(len(contents))
        # print(contents)
        # decoded = base64.b64decode(content_string).decode('utf-8')
        # file_extension = contents.split('.')[-1]
        if 'xes' in filename:
            decoded = base64.b64decode(content_string)
            upload_folder = 'uploads'
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            with open(os.path.join(upload_folder, 'temp.xes'), 'wb') as f:
                f.write(decoded)
            log = read_xes('uploads/temp.xes')
      
        elif 'csv' in filename:
            decoded = base64.b64decode(content_string).decode('utf-8')
            log = read_csv(io.StringIO(decoded), case_id_col, activity_col, timestamp_col)

        # Apply filters
        filtered_log = log  # Implement your filtering logic here

        # Apply mining algorithm
        if algorithm == 'inductive_miner':
            net, im, fm = pm4py.discover_petri_net_inductive(log)
            bpmn_graph = pm4py.convert_to_bpmn(net, im, fm)

        # Visualize BPMN model
        # process_model = pm4py.discover_bpmn_inductive(filtered_log)

        # bpmn_graph = pm4py.convert_to_bpmn(tree)
        image_path = 'images/bpmn.png'
        pm4py.save_vis_bpmn(bpmn_graph,image_path) 
        # pil_image = Image.open("images/bpmn.png")
        encoded_image = base64.b64encode(open(image_path, 'rb').read()).decode('utf-8')
        return  [html.Img(src=f'data:image/png;base64,{encoded_image}', style={'width': '100%'})]
    elif contents is not None and update_checkbox == 'petri':
        content_type, content_string = contents.split(',')
        # file_extension = contents.split('.')[-1]
        if 'xes' in filename:
            decoded = base64.b64decode(content_string)
            upload_folder = 'uploads'
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            with open(os.path.join(upload_folder, 'temp.xes'), 'wb') as f:
                f.write(decoded)
            log = read_xes('uploads/temp.xes')
            
        elif 'csv' in filename:
            decoded = base64.b64decode(content_string).decode('utf-8')
            log = read_csv(io.StringIO(decoded), case_id_col, activity_col, timestamp_col)

        # Apply filters
        filtered_log = log  # Implement your filtering logic here

        # Apply mining algorithm
        if algorithm == 'inductive_miner':
            net, im, fm = pm4py.discover_petri_net_inductive(log)

        # Visualize BPMN model
        # process_model = pm4py.discover_bpmn_inductive(filtered_log)

        # bpmn_graph = pm4py.convert_to_bpmn(tree)
        image_path = 'images/petri.png'
        pm4py.save_vis_petri_net(net, im, fm,image_path) 
        # pil_image = Image.open("images/bpmn.png")
        encoded_image = base64.b64encode(open(image_path, 'rb').read()).decode('utf-8')
        return  [html.Img(src=f'data:image/png;base64,{encoded_image}', style={'width': '100%'})]
    return []

def update_petri(contents, case_id_col, activity_col, timestamp_col, filter_range, algorithm, update_checkbox,filename):
    if contents is not None and update_checkbox == 'petri':
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string).decode('utf-8')
        # file_extension = contents.split('.')[-1]
        if 'xes' in filename:
            log = read_xes(io.StringIO(decoded))
        elif 'csv' in filename:
            log = read_csv(io.StringIO(decoded), case_id_col, activity_col, timestamp_col)

        # Apply filters
        filtered_log = log  # Implement your filtering logic here

        # Apply mining algorithm
        if algorithm == 'inductive_miner':
            net, im, fm = pm4py.discover_petri_net_inductive(log)

        # Visualize BPMN model
        # process_model = pm4py.discover_bpmn_inductive(filtered_log)

        # bpmn_graph = pm4py.convert_to_bpmn(tree)
        image_path = 'images/petri.png'
        pm4py.save_vis_petri_net(net, im, fm,image_path) 
        # pil_image = Image.open("images/bpmn.png")
        encoded_image = base64.b64encode(open(image_path, 'rb').read()).decode('utf-8')
        return  [html.Img(src=f'data:image/png;base64,{encoded_image}', style={'width': '100%'})]
    return []

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)