import pandas
import dash
from dash.dependencies import Input, Output
from dash import dcc
from dash import html

df = pandas.read_csv("./outputs/ArchiveFinal.csv", index_col="Timestamp")
titles=list(df.columns)
myoptions = []
for t in titles:
    myoptions.append({'label': t, 'value': t})

app = dash.Dash('Hello World',
                external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

app.layout = html.Div([
    dcc.Dropdown(
        id='my-dropdown',
        options=myoptions,  
        value='_Sum'
    ),  
    dcc.Graph(id='my-graph')
], style={'width': '500'})

@app.callback(Output('my-graph', 'figure'), [Input('my-dropdown', 'value')])
def update_graph(selected_dropdown_value):  
    return {
        'data': [{
            'x': df.index,
            'y': df[selected_dropdown_value]
        }], 
        'layout': {'margin': {'l': 40, 'r': 0, 't': 20, 'b': 30}}
    }   

if __name__ == '__main__':
    app.run_server()
