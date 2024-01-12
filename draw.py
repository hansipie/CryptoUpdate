import pandas as pd
import dash
import sqlite3
from dash.dependencies import Input, Output
from dash import dcc
from dash import html  

con = sqlite3.connect('./data/db.sqlite3')
df_tokens = pd.read_sql_query("SELECT DISTINCT token from Database;", con)
df_timestamp = pd.read_sql_query("SELECT DISTINCT timestamp from Database ORDER BY timestamp", con)
dfall = pd.DataFrame(columns=['datetime', 'value'])
for mytime in df_timestamp['timestamp']:
    df = pd.read_sql_query("SELECT ROUND(sum(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END)), 2) as value, DATETIME(timestamp, 'unixepoch') AS datetime from Database WHERE timestamp = " + str(mytime), con)
    dfall.loc[len(dfall)] = [df['datetime'][0], df['value'][0]]
con.close()

titles=list(df_tokens['token'])
titles.sort()
myoptions = [{'label': 'All', 'value': 'All'}]
for t in titles:
    myoptions.append({'label': t, 'value': t})

app = dash.Dash('Hello World',
                external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

@app.callback(Output('my-graph', 'figure'), [Input('my-dropdown', 'value')])
def update_graph(selected_dropdown_value):
    print("selected:", selected_dropdown_value)
    if selected_dropdown_value == 'All':
        dff = dfall
        print(dff.tail())
    else:
        con = sqlite3.connect('./data/db.sqlite3')
        dff = pd.read_sql_query("SELECT DATETIME(timestamp, 'unixepoch') AS datetime, ROUND(price*(CASE WHEN count IS NOT NULL THEN count ELSE 0 END), 2) AS value FROM Database WHERE token = '"+selected_dropdown_value+"' ORDER BY timestamp;", con)
        print(dff.tail())
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
        value='All'
    ),  
    dcc.Graph(id='my-graph')
], style={'width': '500'})

if __name__ == '__main__':
    app.run_server()