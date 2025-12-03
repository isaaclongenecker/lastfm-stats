import pylast

# ----------------------------------------------------
# REPLACE THESE WITH YOUR OWN CREDENTIALS
# ----------------------------------------------------
API_KEY = "4b37a3e91a238d2b151f989413530cd8"
API_SECRET = "a0ef0c5226b0ce1be78fababc3206be2"
LASTFM_USERNAME = "isaaclongenecke" # Your Last.fm display name
# ----------------------------------------------------

# 1. Connect to the Last.fm network
network = pylast.LastFMNetwork(
    api_key=API_KEY,
    api_secret=API_SECRET
)

# 2. Get the user object
user = network.get_user(LASTFM_USERNAME)

print(f"--- Stats for User: {LASTFM_USERNAME} ---")
# --- Get Top Artists (All Time) ---
try:
    top_artists = user.get_top_artists(limit=10)

    print("\n\n🏆 Top 10 All-Time Artists:")
    
    # top_artists is a list of tuples (artist_object, play_count)
    for rank, (artist, play_count) in enumerate(top_artists, 1):
        print(f"#{rank}: {artist.name} ({play_count} scrobbles)")

except Exception as e:
    print(f"An error occurred while fetching artists: {e}")
    # --- Get Top Tracks (Last 7 Days) ---
try:
    # Use pylast.PERIOD_7DAYS constant for the last week
    top_tracks = user.get_top_tracks(limit=5, period=pylast.PERIOD_7DAYS) 
    
    print("\n\n🎶 Top 5 Tracks (Last 7 Days):")
    for rank, (track, play_count) in enumerate(top_tracks, 1):
        # We access track name and the associated artist's name
        print(f"#{rank}: {track.title} by {track.artist.name} ({play_count} scrobbles)")

except Exception as e:
    print(f"An error occurred while fetching 7-day tracks: {e}")



# --- Get Top Tracks (Last 365 Days / 12 Months) ---
try:
    # Use pylast.PERIOD_12MONTHS constant for the last year
    # We set a limit of 10 to keep the output clean
    top_year_tracks = user.get_top_tracks(limit=10, period=pylast.PERIOD_12MONTHS) 
    
    print("\n\n🎉 Top 10 Tracks (Last 365 Days):")
    
    # top_year_tracks is a list of tuples (track_object, play_count)
    for rank, (track, play_count) in enumerate(top_year_tracks, 1):
        # Access track name and the associated artist's name
        print(f"#{rank}: {track.title} by {track.artist.name} ({play_count} scrobbles)")

except Exception as e:
    print(f"An error occurred while fetching 365-day tracks: {e}")
# --- Get Top Albums (Last 365 Days / 12 Months) ---
try:
    # Use pylast.PERIOD_12MONTHS and set a limit for the output
    top_year_albums = user.get_top_albums(limit=10, period=pylast.PERIOD_12MONTHS) 
    
    print("\n\n📀 Top 10 Albums (Last 365 Days):")
    
    # top_year_albums is a list of tuples (album_object, play_count)
    for rank, (album, play_count) in enumerate(top_year_albums, 1):
        # Album objects have .name and also contain the .artist object
        print(f"#{rank}: {album.title} by {album.artist.name} ({play_count} scrobbles)")

except Exception as e:
    print(f"An error occurred while fetching 365-day albums: {e}")




    # --- Get Basic User Information ---
    import pylast
# --- Get Basic User Information ---
from datetime import datetime
try:
    # get_playcount() gives the all-time total scrobbles
    total_scrobbles = user.get_playcount() 
    
    print(f"\n\n👤 User Summary:")
    print(f"Total All-Time Scrobbles: {total_scrobbles}")
    
    # get_registered() returns a timestamp, which we convert to a readable format
    registration_date_timestamp = user.get_registered()
    registration_date = datetime.fromtimestamp(int(registration_date_timestamp))
    print(f"Registered on: {registration_date.strftime('%B %d, %Y')}")
    
    # get_now_playing() will return the currently playing track object or None
    current_track = user.get_now_playing()
    if current_track:
        print(f"Listening now: {current_track.title} by {current_track.artist.name}")
    else:
        print("Listening now: (Nothing currently scrobbling)")

except Exception as e:
    print(f"An error occurred while fetching user summary: {e}")

# --- Get Recently Played Tracks ---
try:
    # Get the 5 most recent tracks (including the one currently playing)
    recent_tracks = user.get_recent_tracks(limit=5)
    
    print("\n\n⏱️ Last 5 Played Tracks:")
    for track_object in recent_tracks: # Renamed the variable to 'track_object' for clarity
        
        # Access the track name via .track.title
        track_name = track_object.track.title
        # Access the artist name via .track.artist.name
        artist_name = track_object.track.artist.name 
        
        # The track object has a 'playback_date' attribute
        date = track_object.playback_date or "Now Playing" 
        
        print(f"  - {track_name} by {artist_name} | Scrobble Time: {date}")

except Exception as e:
    print(f"An error occurred while fetching recent tracks: {e}")