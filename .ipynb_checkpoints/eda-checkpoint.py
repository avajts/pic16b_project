import sqlite3
import pandas as pd
from plotly import express as px

def genre_plot(db, genres, col):
    
    """
    takes the database, list of genres, and column to plot as arguments. Note: col should be a string
    returns a figure showing a boxplot of the column by genre
    """
    
    genres_tup = tuple(genres)       
    
    cmd = f"""SELECT {col}, track_genre FROM spotify_tracks WHERE track_genre IN {genres_tup}"""
    with sqlite3.connect(db) as conn:
        df = pd.read_sql_query(cmd, conn)
    fig = px.box(df, x = 'track_genre', y = col, color = 'track_genre', width = 700, height = 400)
    return fig