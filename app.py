import pylast
import os
import requests
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
        api_secret=API_SECRET,
        username=LASTFM_USERNAME
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

def find_artist_in_my_history(names):
    """Looks through my all-time artists, most played first, for any of these names."""
    wanted = {name.strip().lower() for name in names}
    page = 1

    while True:
        response = requests.get(
            'https://ws.audioscrobbler.com/2.0/',
            params={
                'method': 'user.gettopartists',
                'user': LASTFM_USERNAME,
                'api_key': API_KEY,
                'period': 'overall',
                'limit': 1000,
                'page': page,
                'format': 'json',
            },
            timeout=15,
        )
        response.raise_for_status()
        top_artists = response.json()['topartists']

        artists = top_artists.get('artist', [])
        if isinstance(artists, dict):  # Last.fm skips the list when a page has one artist
            artists = [artists]

        for artist in artists:
            if artist['name'].lower() in wanted:
                return artist['name'], int(artist['playcount'])

        if page >= int(top_artists['@attr']['totalPages']):
            return None, 0
        page += 1

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

            # Find the official artist name, which also helps with small typos
            results = network.search_for_artist(artist_query).get_next_page()
            names_to_check = [artist_query]
            if results:
                names_to_check.append(results[0].get_name())

            # Look for the typed name or the official name in my listening history
            my_artist, playcount = find_artist_in_my_history(names_to_check)

            if my_artist:
                search_result = f"Yes! I've listened to {my_artist} {playcount} time{'s' if playcount != 1 else ''}."
            elif results:
                search_result = f"Nope, I haven't listened to {results[0].get_name()} yet."
            else:
                search_result = f"Could not find an artist named '{artist_query}'."

        except Exception as e:
            print(f"Search Error: {e}", flush=True)
            search_result = "Sorry, something went wrong with that search."

    return render_template('stats.html', data=data, search_result=search_result)

if __name__ == '__main__':
    app.run(debug=True)
