import pandas as pd
import dash
import sqlite3
from dash.dependencies import Input, Output
from dash import dcc
from dash import html  

con = sqlite3.connect('./outputs/db.sqlite3')
df_tokens = pd.read_sql_query("SELECT DISTINCT token from Database;", con)
con.close()

titles=list(df_tokens['token'])
myoptions = []
for t in titles:
    myoptions.append({'label': t, 'value': t})

app = dash.Dash('Hello World',
                external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

@app.callback(Output('my-graph', 'figure'), [Input('my-dropdown', 'value')])
def update_graph(selected_dropdown_value):
    print("selected:", selected_dropdown_value)
    con = sqlite3.connect('./outputs/db.sqlite3')
    dff = pd.read_sql_query("SELECT ROUND(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END), 2) AS value, DATETIME(timestamp, 'unixepoch') AS datetime FROM Database WHERE token = '"+selected_dropdown_value+"' ORDER BY timestamp;", con)
    print(dff.head())
    con.close()
    return {
        'data': [{
            'x': dff['datetime'],
            'y': dff['value']
        }], 
        'layout': {'margin': {'l': 40, 'r': 0, 't': 20, 'b': 30}}
    } 

app.layout = html.Div([
    dcc.Dropdown(
        id='my-dropdown',
        options=myoptions,  
        value='BTC'
    ),  
    dcc.Graph(id='my-graph')
], style={'width': '500'})

if __name__ == '__main__':
    app.run_server()