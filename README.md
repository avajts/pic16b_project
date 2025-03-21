# Spotify Collaborative Playlist Generator

## Overview
This project is a Flask-based web application that allows users to generate collaborative Spotify playlists based on their combined or individual listening history. The app integrates with the Spotify API to fetch a user's playlists and recommend songs from a [Kaggle](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset/data) dataset of Spotify songs using a K-Nearest Neighbors (KNN) machine learning model.

## Features
* **Spotify API Integration:** Fetch user playlists and tracks.
* **SQL Database Management:** Store users data and Spotify track data in SQL database.
* **Machine Learning-Based Recommendations:** Uses KNN to suggest new songs based on listening habits.
* **Interactive Data Visualizations:** Provides insights into a user's music preferences.
* **Flask Web Interface:** Runs locally and provides an easy-to-use interface.

## Installation
### Step 1: Clone the Repository
Open your terminal and run:

```
git clone https://github.com/avajts/pic16b_project.git
cd pic16b_project
```

Step 2: Install Flask

```
pip install Flask
```

### Step 3: Set Up Flask Environment
For Windows:

```
set FLASK_APP=main.py
```

For macOS/Linux:

```
export FLASK_APP=main.py
```

### Step 4: Run the Application

```
flask run
```

After running this command, you will see an HTTPS link in your terminal. Open it in your browser to access the app.

## Usage
1. Login with Spotify: The app will request permission to access your playlists.
2. Generate a Playlist: Select a genre and the number of recommended songs.
3. View Insights: Explore data visualizations on your listening habits.

## Technical Details
* Flask: Web framework used to create the application.
* SQLite: Stores user playlist data locally.
* Spotify API: Fetches user playlists and track details.
* Plotly: Generates interactive visualizations.
* Machine Learning: KNN is used to recommend songs based on user preferences.
