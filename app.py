import pylast
from datetime import datetime
from flask import Flask, render_template
import os # <-- ADD THIS LINE

# ----------------------------------------------------
# NOW WE READ SECRETS FROM THE ENVIRONMENT
# ----------------------------------------------------
API_KEY = os.environ.get('4b37a3e91a238d2b151f989413530cd8')
API_SECRET = os.environ.get('a0ef0c5226b0ce1be78fababc3206be2')
LASTFM_USERNAME = os.environ.get('isaaclongenecke') # Your Last.fm display name
# ----------------------------------------------------

# Initialize the Flask application
app = Flask(__name__)
# ... rest of your code ...


import pylast
from datetime import datetime
from flask import Flask, render_template

# ----------------------------------------------------
# REPLACE THESE WITH YOUR OWN CREDENTIALS
# ----------------------------------------------------
API_KEY = "4b37a3e91a238d2b151f989413530cd8"
API_SECRET = "a0ef0c5226b0ce1be78fababc3206be2"
LASTFM_USERNAME = "isaaclongenecke" # Your Last.fm display name
# ----------------------------------------------------

# Initialize the Flask application
app = Flask(__name__)

def get_lastfm_stats():
    """Fetches all necessary Last.fm data."""
    
    # 1. Connect to the Last.fm network
    network = pylast.LastFMNetwork(
        api_key=API_KEY,
        api_secret=API_SECRET
    )

    # 2. Get the user object
    user = network.get_user(LASTFM_USERNAME)
    
    # This dictionary will hold all the data we want to pass to the website
    stats_data = {}

    # --- 1. User Summary ---
    stats_data['username'] = LASTFM_USERNAME
    stats_data['total_scrobbles'] = user.get_playcount() 
    registration_date_timestamp = user.get_registered()
    stats_data['registered_on'] = datetime.fromtimestamp(int(registration_date_timestamp)).strftime('%B %d, %Y')
    
    # --- 2. Top Artists (All Time) ---
    top_artists = user.get_top_artists(limit=5)
    # Store data as a list of dicts for easy use in the website
    stats_data['top_artists'] = [
        {'name': artist.name, 'scrobbles': play_count} 
        for artist, play_count in top_artists
    ]

    # --- 3. Top Albums (Last 365 Days) ---
    top_year_albums = user.get_top_albums(limit=5, period=pylast.PERIOD_12MONTHS) 
    # Use the corrected access: album.title
    stats_data['top_albums'] = [
        {'title': album.title, 'artist': album.artist.name, 'scrobbles': play_count} 
        for album, play_count in top_year_albums
    ]
    
    return stats_data

# The main route for the website
@app.route('/')
def index():
    # Call the function to get the data
    data = get_lastfm_stats()
    
    # Render the HTML template (which we'll create next)
    # The 'data=data' passes the Python dictionary to the HTML template
    return render_template('stats.html', data=data)

if __name__ == '__main__':
    # Run the web server
    app.run(debug=True)