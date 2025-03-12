from flask import Flask, redirect, request, jsonify, session, render_template
import requests
import urllib.parse
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
import json
from music_rec import prep_dfs, remove_duplicates, recommend_songs
from eda import two_var_plot, genre_hist
import plotly.express as px
from plotly import utils
import re


app = Flask(__name__)
app.secret_key = 'li23j4-23423h-45896jgahnv'


CLIENT_ID = '730dd1d43d7d405ca08272b74e8cffe7'
CLIENT_SECRET = '88066f09daaf4676a83ebdf1f4b694fa'
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'


@app.route('/')

def index():
    return render_template('index.html')


@app.route('/login')

def login():
    scope = 'playlist-read-private playlist-read-collaborative'
    #user-read-private user-read-email
    params = {
            'client_id': CLIENT_ID,
            'response_type': 'code',
            'scope': scope,
            'redirect_uri': REDIRECT_URI,
            'show_dialog': True
            }

    auth_url = f'{AUTH_URL}?{urllib.parse.urlencode(params)}'

    return redirect(auth_url)


@app.route('/callback')

def callback():

    if 'error' in request.args:
        return jsonify({'error': request.args['error']})

    if 'code' in request.args:
        req_body = {
                'code': request.args['code'],
                'grant_type': 'authorization_code',
                'redirect_uri': REDIRECT_URI,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET
                }

    response = requests.post(TOKEN_URL, data=req_body)
    token_info = response.json()

    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

    return redirect('/playlists')


@app.route('/playlists')

def get_playlists():
    if 'access_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')

    headers = {
            'Authorization': f"Bearer {session['access_token']}"
    }
    response = requests.get(API_BASE_URL + 'me/playlists', headers = headers)
    print("STATUS CODE: ", response.status_code)
    playlists = response.json()
    
    #put into df in order to write to SQL database
    playlists_df = pd.json_normalize(playlists['items']) 
    playlists_cols = ['id', 'href', 'description', 'name', 
                                 'owner.id', 'owner.display_name', 'tracks.href']
    playlists_df = playlists_df[playlists_cols]
    playlists_df.rename(columns = {col : col.replace('.', '_') for col in playlists_cols}, inplace = True)
    print(playlists_df.info())
    
    tracks = []
    keys = []
    for x in playlists['items']:
        response = requests.get(x['tracks']['href'], headers = headers)
        data = response.json()
        temp = pd.json_normalize(data['items'])
        temp['playlist.id'] = x['id']
        tracks.append(temp)
    tracks_df = pd.concat(tracks)
    tracks_cols = ['playlist.id', 'track.id', 'track.explicit', 'track.album.id', 'track.artists', 
                          'track.duration_ms', 'track.href', 'track.name', 'track.popularity']
    tracks_df = tracks_df[tracks_cols]
    tracks_df.rename(columns = {col : col.replace('.', '_') for col in tracks_cols}, inplace = True)
    for col in tracks_df.columns:
        tracks_df[col] = tracks_df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x) #convert list-like data  types for sql

    # print(tracks_df.info())
    
    
    #get user's username so they can have their own table in the database
    headers = {
            'Authorization': f"Bearer {session['access_token']}"
    }
    response = requests.get(API_BASE_URL + 'me', headers = headers)
    print("STATUS CODE: ", response.status_code)
    user_info = response.json()
    username = user_info['display_name']
    tracks_df['username'] = username
    playlists_df['username'] = username
    
    with sqlite3.connect('spotify_dataset.db') as conn:
        playlists_df.to_sql("user_playlists", conn, if_exists = "append", index = False) # one table for playlists and one for tracks
        tracks_df.to_sql(name="user_tracks", con=conn, if_exists = "append", index = False)
        display = pd.read_sql_query('''
        SELECT user_tracks.track_name, user_tracks.track_artists 
        FROM user_tracks INNER JOIN spotify_tracks 
        ON user_tracks.track_id = spotify_tracks.track_id;''', conn)
    
    #extract artist names for display table
    display['track_artists'] = (display['track_artists'].str.findall(r'\bname": "([^"]*)')).apply(lambda x: str(x))
    display.drop_duplicates(inplace=True)

    display_table = display.to_html(classes='table table-striped', index=False)

    return render_template('playlist.html', table=display_table)


@app.route('/refresh-token')

def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

    response = requests.post(TOKEN_URL, data = req_body)
    new_token_info = response.json()
    
    session['access_token'] = new_token_info['access_token']
    session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

    return redirect('/playlists')



@app.route('/display-recommended', methods=['GET', 'POST'])

def display_recommended():
    with sqlite3.connect("spotify_dataset.db") as conn:
        df_spotify_tracks = pd.read_sql_query("SELECT * FROM spotify_tracks;", conn)
        df_user_playlists = pd.read_sql_query("SELECT * FROM user_playlists;", conn)
        df_user_tracks = pd.read_sql_query("SELECT * FROM user_tracks;", conn)

    user_df, df_spotify_tracks = prep_dfs()

    features = ['danceability', 'energy', 'tempo', 'speechiness', 'acousticness', 'instrumentalness', 'valence', 'loudness']
    df_users_filtered = user_df[features]

    if request.method == 'POST':
        genre = request.form.get('genre', None)
        n = request.form.get('n', '30')

        try:
            n = int(n)  # Convert to integer
        except ValueError:
            return "Error: n must be an integer.", 400  # Handle invalid numbers

        if n <= 0:
            return "Error: n must be a positive integer.", 400

        # Generate the recommended playlist
        recommended = recommend_songs(df_users_filtered, df_spotify_tracks, genre=genre, n=n)
    
        # Convert DataFrame to HTML
        recommended_html = recommended.to_html(classes='table table-striped', index=False)
    
        return render_template('display_recommended.html', table=recommended_html)

    return render_template('input_form.html')  # Show form if GET request



@app.route('/display-data', methods=['GET', 'POST'])
def display_data():
    
    """
    if user clicks on button to prompt this, it will display some visualizations about the users' music
    visualizations can be customized
    """
    # Get the data into dataframes
    with sqlite3.connect("spotify_dataset.db") as conn:
        df_spotify_tracks = pd.read_sql_query("SELECT * FROM spotify_tracks;", conn)
        df_user_playlists = pd.read_sql_query("SELECT * FROM user_playlists;", conn)
        df_user_tracks = pd.read_sql_query("SELECT * FROM user_tracks;", conn)

    user_df, df_spotify_tracks = prep_dfs()
    
    if request.method == 'POST':
        plot = request.form.get('plot', None)
        features = [request.form.get('feature0', 'loudness'), request.form.get('feature1', 'energy')]
        genre = request.form.get('genre', 'pop')
        
        if plot == 'two_var_plot':
            # Create the Plotly figures
            fig = two_var_plot(user_df, features)
    
            # Convert the Plotly figure to JSON
            graph_json = json.dumps(fig, cls=utils.PlotlyJSONEncoder)
    
            # Render the template with the graph JSON
            return render_template('two_var_plot.html', graph_json=graph_json)
        
        elif plot == 'genre_hist':
            fig = genre_hist(user_df)
            graph_json = json.dumps(fig, cls=util.PlotlyJSONEncoder)
            return render_template('genre_hist.html', graph_json=graph_json)
    
    else: return render_template('data_input.html')
    