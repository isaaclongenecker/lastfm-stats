import pylast
import os
from datetime import datetime
from flask import Flask, render_template, request

# --- 1. SET UP CREDENTIALS ---
# These must match the "Keys" you created in your Render Environment settings
API_KEY = os.environ.get('LASTFM_API_KEY')
API_SECRET = os.environ.get('LASTFM_API_SECRET')
LASTFM_USERNAME = os.environ.get('LASTFM_USERNAME')

app = Flask(__name__)

def get_lastfm_stats():
    """Fetches all necessary Last.fm data for the dashboard."""
    
    # Connect to the Last.fm network
    network = pylast.LastFMNetwork(
        api_key=API_KEY,
        api_secret=API_SECRET
    )

    user = network.get_user(LASTFM_USERNAME)
    stats_data = {}

    # --- User Summary ---
    stats_data['username'] = LASTFM_USERNAME
    stats_data['total_scrobbles'] = user.get_playcount() 
    reg_date = user.get_registered()
    stats_data['registered_on'] = datetime.fromtimestamp(int(reg_date)).strftime('%B %d, %Y')
    
    # --- Top Artists (All Time) ---
    top_artists = user.get_top_artists(limit=10)
    stats_data['top_artists'] = [
        {'name': artist.name, 'scrobbles': play_count} 
        for artist, play_count in top_artists
    ]

    # --- Top Albums (Last Year) ---
    top_year_albums = user.get_top_albums(limit=10, period=pylast.PERIOD_12MONTHS) 
    stats_data['top_albums'] = [
        {'title': album.title, 'artist': album.artist.name, 'scrobbles': play_count} 
        for album, play_count in top_year_albums
    ]
    
    # --- Top Tracks (Last Year) ---
    top_year_tracks = user.get_top_tracks(limit=10, period=pylast.PERIOD_12MONTHS) 
    stats_data['top_tracks'] = [
        {'title': track.title, 'artist': track.artist.name, 'scrobbles': play_count}
        for track, play_count in top_year_tracks
    ]

    # --- Recently Played Tracks ---
    recent_tracks = user.get_recent_tracks(limit=6)
    stats_data['recent_tracks'] = [
        {
            'title': track_obj.track.title,
            'artist': track_obj.track.artist.name,
            'date': track_obj.playback_date or "Now Playing" 
        }
        for track_obj in recent_tracks
    ]

    # --- Currently Playing ---
    current = user.get_now_playing()
    stats_data['now_playing'] = "(Nothing currently scrobbling)"
    stats_data['now_playing_image'] = "" 

    if current:
        stats_data['now_playing'] = f"{current.title} by {current.artist.name}"
        try:
            stats_data['now_playing_image'] = current.get_cover_image()
        except Exception:
            pass

    return stats_data

@app.route('/', methods=['GET', 'POST'])
def index():
    # 1. Fetch general dashboard stats
    data = get_lastfm_stats()
    search_result = None

  # 2. Handle the "Have I listened to..." search bar logic
    artist_query = request.args.get('artist_name')
    if artist_query:
        try:
            network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET)
            
            # 1. Find the official artist name first
            search = network.search_for_artist(artist_query)
            results = search.get_next_page()
            
            if results:
                official_artist = results[0]
                official_name = official_artist.get_name()
                
                # 2. Look specifically in your library for this artist
                library = network.get_library(LASTFM_USERNAME)
                
                # This returns the playcount as an integer directly
                playcount = library.get_userplaycount(official_artist)
                
                if playcount and int(playcount) > 0:
                    search_result = f"Yes! I've listened to {official_name} {playcount} times."
                else:
                    search_result = f"Nope, I haven't listened to {official_name} yet."
            else:
                search_result = f"Could not find an artist named '{artist_query}'."
                
        except Exception as e:
            print(f"Search Error: {e}")
            search_result = "Sorry, I couldn't find that artist."

    return render_template('stats.html', data=data, search_result=search_result)

if __name__ == '__main__':
    app.run(debug=True)