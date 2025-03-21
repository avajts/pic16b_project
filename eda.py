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

def two_var_plot(df, features):
    x = features[0]
    y = features[1]
    fig = px.scatter(df, x, y, title=f'{x} vs. {y}', color='username', hover_data=['track_name', 'track_artists'])
    return fig

def genre_hist(df):
    fig = px.histogram(df, 'track_genre', facet_col='username', color='track_genre')
    return fig

def plot_correlation_heatmap(df):
    """
    Generates and displays a correlation heatmap for numerical track features in the given Spotify dataset.
    
    Parameters:
        df (pd.DataFrame): The Spotify dataset containing track features.
    
    Returns:
        None
    """
    # Extract numerical columns
    numerical_cols = df.select_dtypes(include=['number']).columns.tolist()
    num_df = df[numerical_cols]
    
    # Compute correlation matrix
    corr_matrix = num_df.corr()
    
    # Create heatmap using Plotly
    fig = px.imshow(corr_matrix,
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    title="Correlation Matrix Heatmap")

    # Adjust layout
    fig.update_layout(
        xaxis_title="",
        yaxis_title="",
        width=800,
        height=800
    )

    # Show the heatmap
    fig.show()


def plot_genre_count(df):
    fig = px.histogram(df, 'track_genre', color='track_genre')
    fig.show()

