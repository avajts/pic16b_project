import sqlite3
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error


def prep_dfs():
    '''
    Removes duplicates in sql tables spotify_tracks,
    user_playlists, and user_tracks by calling remove_duplicates
    function.
    Returns:
    df_all_tracks: df of user songs that are also in Kaggle dataset
    df_spotify_tracks: df of Kaggle Spotify songs
    '''
    with sqlite3.connect("spotify_dataset.db") as conn:
        df_spotify_tracks = pd.read_sql_query("SELECT * FROM spotify_tracks;", conn)
        df_user_playlists = pd.read_sql_query("SELECT * FROM user_playlists;", conn)
        df_user_tracks = pd.read_sql_query("SELECT * FROM user_tracks;", conn)

    #Remove duplicates
    remove_duplicates(df_spotify_tracks, ['track_name', 'artists'])
    remove_duplicates(df_user_playlists, ['name', 'description'])
    remove_duplicates(df_user_tracks, ['track_name', 'track_popularity'])

    #Create df that has user songs that are also in Kaggle dataset
    df_all_tracks = pd.DataFrame()
    print(len(df_all_tracks))

    for i in range(len(df_user_tracks)):
        value = df_user_tracks.loc[i, 'track_id']
        if value in df_spotify_tracks['track_id'].values:
            result = df_spotify_tracks.loc[df_spotify_tracks['track_id'] == value]
            df_all_tracks = pd.concat([df_all_tracks, result], ignore_index=True)
        
    return df_all_tracks, df_spotify_tracks


def remove_duplicates(df, subset):
    '''
    Removes duplicate rows from dataframes and resets the index.
    Args:
    df: the dataframe you want to remove duplicates from
    subset: which columns you want to find duplicates based on
    '''
    # Count duplicated rows based on track_name and artists
    duplicated_rows = df.duplicated(subset=subset).sum()

    if duplicated_rows == 0:
        print(f'There are 0 duplicate rows based on {subset[0]} and {subset[1]}.')
    else:
        print(f'There are {duplicated_rows} duplicate rows based on {subset[0]} and {subset[1]}. Dropping them now...')
        
        # Drop duplicates based on track_name and artists, keeping the first occurrence
        df = df.drop_duplicates(subset=subset, keep='first')
        # Rest the index of rows
        df = df.reset_index(drop=True)

        rows_left = df.shape[0]
        
        print(f'After dropping duplicates, there are {rows_left} rows left.')





def tune_knn(X_train, X_test, k_values=range(1, 101)):
    """ Function to find the best k value for KNN model
    """
    best_k = None
    best_score = float('inf')  # Lower score is better
    scores = []

    for k in k_values:
        knn = NearestNeighbors(n_neighbors=k, metric='euclidean')
        knn.fit(X_train)
        
        # Find distances to test points
        distances, _ = knn.kneighbors(X_test, n_neighbors=k)
        
        # Compute Mean Squared Error (MSE)
        mse = np.mean(distances**2)
        scores.append((k, mse))
        
        # Track best k
        if mse < best_score:
            best_score = mse
            best_k = k
    
    return best_k, scores



def recommend_songs(user_songs, spotify_tracks, genre=None, n=30):
    """ Function to recommend songs based on playlist
    Args: 
        user_songs: db full of playlists (rows must be >= n)
        genre: string, optional, genre provided by user to group tracks
        n: number of songs being recommended

    Returns:
        recommended_tracks: db which contains the n many recommended songs
    """
    features = ['danceability', 'energy', 'tempo', 'speechiness', 'acousticness', 'instrumentalness', 'valence', 'loudness']
    
    # Filter dataset by genre if specified
    if genre:
        df_spot_filtered = spotify_tracks[spotify_tracks['track_genre'].str.lower() == genre.lower()]
        if df_spot_filtered.empty:
            print(f"Warning: No songs found for genre '{genre}'. Using all genres instead.")
            df_spot_filtered = spotify_tracks  # Fall back to all songs
    else:
        df_spot_filtered = spotify_tracks  # Use all genres if none specified

    # Ensure `n` does not exceed the number of available songs in the dataset
    max_neighbors = min(n, len(df_spot_filtered))  

    # Ensure `user_songs` has enough entries
    num_user_songs = len(user_songs)
    if num_user_songs < max_neighbors:
        print(f"Warning: User provided only {num_user_songs} songs. Adjusting neighbors to {num_user_songs}.")
        max_neighbors = num_user_songs

    # Create and scale the users songs with the given features
    scaler = StandardScaler()
    user_songs_scaled = scaler.fit_transform(user_songs[features])

     # Fit a k-NN model specifically for the filtered dataset
    knn_filtered = NearestNeighbors(n_neighbors=max_neighbors, metric='euclidean')
    knn_filtered.fit(df_spot_filtered[features])

    # Find nearest neighbors
    distances, indices = knn_filtered.kneighbors(user_songs_scaled, n_neighbors=max_neighbors)

    # Get recommended tracks from the filtered dataset
    recommended_tracks = df_spot_filtered.iloc[indices[0]]

    return recommended_tracks[['track_name', 'artists', 'track_genre', 'loudness', 'danceability', 'energy', 'tempo', 'speechiness', 'acousticness', 'instrumentalness', 'valence']]



