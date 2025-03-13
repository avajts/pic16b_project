import sqlite3
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()


def prep_dfs(spotify, tracks):
    '''
    Returns df of users songs that can also be found in Spotify df.
    Args:
        spotify: df of all Spotify songs from Kaggle dataset
        tracks: df of all users songs that may not be in Kaggle dataset
    Returns:
        df_all_tracks: df of user songs that are also in Kaggle dataset
    '''
    #Remove duplicates
    """ Not necessary since we do this in ipynb file, use params"""
    # df_spotify_tracks = remove_duplicates(df_spotify_tracks, ['track_name', 'artists'])
    # df_user_playlist = remove_duplicates(df_user_playlists, ['name', 'description'])
    # df_user_tracks = remove_duplicates(df_user_tracks, ['track_name', 'track_popularity'])

    #Create df that has user songs that are also in Kaggle dataset
    df_all_tracks = pd.DataFrame()
    print(f'length of user_df: {len(df_all_tracks)}')

    for i in range(len(tracks)):
        value = tracks.loc[i, 'track_id']
        if value in tracks['track_id'].values:
            result = spotify.loc[spotify['track_id'] == value]
            df_all_tracks = pd.concat([df_all_tracks, result], ignore_index=True)

    # Encode the 'track_genre' category to get numerical values
    df_all_tracks['track_genre_encoded'] = le.fit_transform(df_all_tracks['track_genre'])
        
    return df_all_tracks


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

    return df





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
        user_songs: df full of playlists (rows must be >= n)
        spotify_tracks: df of all kaggle data
        genre: string, optional, genre provided by user to group tracks
        n: number of songs being recommended

    Returns:
        recommended_tracks: df which contains the n many recommended songs
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


def get_user_df():
    """
    no args
    returns df with user songs that are also in kaggle dataset
    """
    with sqlite3.connect("spotify_dataset.db") as conn:
        user_df = pd.read_sql_query('''
            SELECT * 
            FROM user_tracks INNER JOIN spotify_tracks 
            ON user_tracks.track_id = spotify_tracks.track_id;''', conn)
    
    #remove duplicates
    user_df.drop_duplicates(subset='track_name', ignore_index=True, inplace=True)
    user_df['track_genre_encoded'] = le.fit_transform(user_df['track_genre'])

    #remove duplicate columns
    user_df = user_df.loc[:,~user_df.columns.duplicated()].copy()
    
    #extract artist names
    user_df['track_artists'] = (user_df['track_artists'].str.findall(r'\bname": "([^"]*)')).apply(lambda x: str(x))

    return user_df

def get_spotify_df():
    """
    no args
    returns df of kaggle dataset
    """
    with sqlite3.connect("spotify_dataset.db") as conn:
        spotify_df = pd.read_sql_query('SELECT * FROM spotify_tracks', conn)
    
    return spotify_df.drop_duplicates(subset='track_id', ignore_index=True)
