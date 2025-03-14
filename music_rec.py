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
    NOT RELEVANT TO APP
    Returns df of users songs that can also be found in Spotify df.
    Args:
        spotify: df of all Spotify songs from Kaggle dataset
        tracks: df of all users songs that may not be in Kaggle dataset
    Returns:
        df_all_tracks: df of user songs that are also in Kaggle dataset
    '''
    #Remove duplicates
    spotify = remove_duplicates(spotify, ['track_name', 'artists'])
    tracks = remove_duplicates(tracks, ['track_name', 'track_popularity'])

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
        
    return df_all_tracks, spotify


def remove_duplicates(df, subset):
    '''
    NOT RELEVANT TO APP
    Removes duplicate rows from dataframes and resets the index.
    Args:
        df: the dataframe you want to remove duplicates from
        subset: which columns you want to find duplicates based on
    Returns:
        df: The dataframe with no duplicate songs/rows
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



def recommend_songs(user_songs, spotify_tracks, genre=None, n=30, random_state=42):
    """
    Generate a personalized playlist of `n` songs from a specific genre based on the user's preferences.

    Args:
        df: The user's listening history with audio features.
        genre: The genre of songs to recommend.
        n: The number of songs to recommend (default is 5).
        random_state: Seed for reproducibility (default is 42).

    Returns:
        random_recommendations: A DataFrame containing the recommended songs.
    """
    # Filter the Spotify dataset to include only songs from the specified genre
    genre_tracks = spotify_tracks[spotify_tracks['track_genre'].str.lower() == genre.lower()]

    # Check if there are enough songs in the specified genre
    if len(genre_tracks) < n:
        raise ValueError(f"Not enough songs in the '{genre}' genre. Only {len(genre_tracks)} songs available.")

    # Select relevant features for the KNN model
    features = ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness',
                'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo']

    # Prepare the feature matrix for the user's listening history
    X_user = user_songs[features]

    # Train the KNN model on the user's data
    # Standardize the features
    scaler = StandardScaler()
    X_user_scaled = scaler.fit_transform(X_user)

    # Ensure `n` does not exceed the number of available songs in the dataset
    max_neighbors = min(n, len(X_user_scaled))

    # Train the KNN model on the user's features
    knn = NearestNeighbors(n_neighbors=max_neighbors, metric='euclidean')  # Use Euclidean distance
    knn.fit(X_user_scaled)

    # Prepare the feature matrix for the genre-specific songs
    X_genre = genre_tracks[features]
    X_genre_scaled = scaler.transform(X_genre)

    # Find the nearest neighbors (most similar songs) in the genre-specific dataset
    distances, indices = knn.kneighbors(X_genre_scaled)

    # Flatten the indices array to get a list of all recommended song indices
    recommended_song_indices = indices.flatten()

    # Ensure indices are within the valid range of the genre_tracks DataFrame
    valid_indices = [idx for idx in recommended_song_indices if idx < len(genre_tracks)]

    if not valid_indices:
        raise ValueError("No valid recommendations found. Please check the input data.")

    # Get the recommended songs
    recommended_songs = genre_tracks.iloc[valid_indices].drop_duplicates(subset=['track_name', 'artists']).head(n)

    # Randomly select `n` songs from the recommendations
    random_recommendations = recommended_songs.sample(n=n, random_state=random_state)

    random_recommendations = random_recommendations[['artists', 'track_name', 'track_genre']]

    # Display the recommended songs
    return random_recommendations


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
    user_df.drop_duplicates(subset=['track_name', 'artists'], ignore_index=True, inplace=True)
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
    
    return spotify_df.drop_duplicates(subset=['track_name', 'artists'], ignore_index=True)

def playlist_song_recs(users_playlists, spotify_tracks, playlist, n=5):
    """
    Function to test reccomendation system by inputing user playlist, and recommending 5 songs.
    Args:
        users_playlists: Df that contains the users tracks and their associated playlists (no song metrics)
        spotify tracks: Df that contains all songs in Kaggle dataset wth song metrics
        playlist: User's selected playlist to get recommended songs for
        n: Number of songs to get recommended
    Returns:
        random_recommendations: Df that contains 5 randomly selected songs from list of song recommendations
    """
    # Identify the requested playlist
    requested_playlist_tracks = users_playlists[users_playlists['name'].str.lower() == playlist.lower()]['track_id'].tolist()

    # Extract features for the requested playlist
    requested_playlist_features = spotify_tracks[spotify_tracks['track_id'].isin(requested_playlist_tracks)]

    # Encode track_genre as a numerical feature in both DataFrames
    label_encoder = LabelEncoder()
    spotify_tracks['track_genre_encoded'] = label_encoder.fit_transform(spotify_tracks['track_genre'])
    requested_playlist_features['track_genre_encoded'] = label_encoder.transform(requested_playlist_features['track_genre'])

    # Print the top genres in the requested playlist
    print("Top genres in the requested playlist:")
    print(requested_playlist_features['track_genre'].value_counts())

    # Filter the Spotify dataset to include only songs from the top genres
    main_genres = requested_playlist_features['track_genre'].value_counts().index[:]  # Top 2 genres
    filtered_spotify_tracks = spotify_tracks[spotify_tracks['track_genre'].isin(main_genres)]

    # Select relevant features for the KNN model
    features = ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness',
                'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo']

    # Prepare the feature matrix for the requested playlist
    X_requested = requested_playlist_features[features]

    # Train separate KNN models for each genre
    recommended_songs_by_genre = []

    for genre in main_genres:
        # Filter the requested playlist features for the current genre
        genre_features = requested_playlist_features[requested_playlist_features['track_genre'].str.lower() == genre.lower()]
        
        # Prepare the feature matrix for the current genre
        X_genre = genre_features[features]
        
        # Standardize the features
        scaler = StandardScaler()
        X_genre_scaled = scaler.fit_transform(X_genre)

        # Ensure `n` does not exceed the number of available songs in the dataset
        max_neighbors = min(5, len(X_genre_scaled))  
        
        # Train the KNN model for the current genre
        knn = NearestNeighbors(n_neighbors=max_neighbors, metric='euclidean')  # Use Euclidean distance
        knn.fit(X_genre_scaled)
        
        # Filter the Spotify dataset for the current genre
        genre_spotify_tracks = filtered_spotify_tracks[filtered_spotify_tracks['track_genre'].str.lower() == genre.lower()]
        
        # Prepare the feature matrix for the filtered Spotify dataset
        X_spotify_genre = genre_spotify_tracks[features]
        X_spotify_genre_scaled = scaler.transform(X_spotify_genre)
        
        # Find the nearest neighbors (most similar songs) in the filtered Spotify dataset
        distances, indices = knn.kneighbors(X_spotify_genre_scaled)
        
        # Flatten the indices array to get a list of all recommended song indices
        recommended_song_indices = indices.flatten()
        
        # Filter out tracks already in the requested playlist
        recommended_song_indices = [idx for idx in recommended_song_indices if genre_spotify_tracks.iloc[idx]['track_id'] not in requested_playlist_tracks]
        
        # Get the recommended songs for the current genre
        genre_recommendations = genre_spotify_tracks.iloc[recommended_song_indices].drop_duplicates(subset=['track_id']).head(5)
        
        # Add the recommendations to the list
        recommended_songs_by_genre.append(genre_recommendations)

    # Combine the recommendations
    balanced_recommendations = pd.concat(recommended_songs_by_genre)  # Ensure we have 5 songs in total

    # Ensure `n` does not exceed the number of available songs in the dataset
    max_neighbors = min(5, len(balanced_recommendations))  

    # Randomly select 5 songs from the combined recommendations
    random_recommendations = balanced_recommendations.sample(n=max_neighbors, random_state=42)  # Use random_state for reproducibility

    return random_recommendations
