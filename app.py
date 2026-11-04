import pylast
import os
import time
import requests
from urllib.parse import quote
from flask import Flask, render_template, request

# --- 1. SET UP CREDENTIALS ---
# These must match the "Keys" you created in your Render Environment settings
API_KEY = os.environ.get('LASTFM_API_KEY')
API_SECRET = os.environ.get('LASTFM_API_SECRET')
LASTFM_USERNAME = os.environ.get('LASTFM_USERNAME')

# The name shown at the top of the page
DISPLAY_NAME = 'Isaac Longenecker'

# An artist counts as "a lot lately" if, over the last month, they are
# in my top LATELY_TOP_ARTISTS and have at least LATELY_MIN_SCROBBLES plays
LATELY_TOP_ARTISTS = 25
LATELY_MIN_SCROBBLES = 10

# "Haven't played in a while" means no plays during this period
# (Last.fm's choices are 1month, 3month, 6month, and 12month)
NOT_PLAYED_PERIOD = '6month'

# "Recently discovered" means nearly all of an artist's plays happened during
# this period, and they have at least DISCOVERED_MIN_PLAYS plays
DISCOVERED_PERIOD = '3month'
DISCOVERED_MIN_PLAYS = 3

# The plain-English names of Last.fm's time periods, used in the tag definitions
PERIOD_WORDS = {'1month': 'month', '3month': '3 months', '6month': '6 months', '12month': '12 months'}

# The definitions that pop up over each tag
BADGE_DEFINITIONS = {
    'Favorite': 'One of my top 25 artists of all time.',
    'Likes them': 'One of my top 50 artists of all time.',
    'Heard before': 'One of my top 100 artists of all time.',
    'Heavy rotation': f'One of my top {LATELY_TOP_ARTISTS} artists over the last month, with at least {LATELY_MIN_SCROBBLES} plays.',
    'Recently discovered': f'Nearly all of my plays of this artist came in the last {PERIOD_WORDS[DISCOVERED_PERIOD]}.',
    "Haven't played in a while": f"I've played this artist before, but not in the last {PERIOD_WORDS[NOT_PLAYED_PERIOD]}.",
    'Recommend it to me': "I haven't played this artist yet, so it could be a good recommendation.",
}

app = Flask(__name__)


@app.template_filter('spotify_search')
def spotify_search(text):
    """Makes a link that searches Spotify for this text."""
    return 'https://open.spotify.com/search/' + quote(text, safe='')


# Last.fm uses this image when it has no real artwork
PLACEHOLDER_IMAGE = '2a96cbd8b46e442fc41c2b86b821562f'

# Remembers recent answers from Last.fm so the page loads faster
_cache = {}


def cached(name, seconds, loader, default):
    """Reuses a recent result. If Last.fm fails, keeps the page working."""
    saved = _cache.get(name)
    if saved and time.time() - saved['time'] < seconds:
        return saved['value']
    try:
        value = loader()
        _cache[name] = {'time': time.time(), 'value': value}
        return value
    except Exception as e:
        print(f"Could not load {name}: {e}", flush=True)
        return saved['value'] if saved else default


def lastfm_get(method, **params):
    """Sends one request to Last.fm and returns the answer."""
    params.update({
        'method': method,
        'user': LASTFM_USERNAME,
        'api_key': API_KEY,
        'format': 'json',
    })
    response = requests.get('https://ws.audioscrobbler.com/2.0/', params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def as_list(value):
    """Last.fm skips the list when there is only one item."""
    if not value:
        return []
    return [value] if isinstance(value, dict) else value


def best_image(item):
    """Returns the largest real image Last.fm gave us, or an empty string."""
    images = {image.get('size'): image.get('#text', '') for image in as_list(item.get('image'))}
    for size in ('extralarge', 'large', 'medium', 'small'):
        url = images.get(size, '')
        if url and PLACEHOLDER_IMAGE not in url:
            return url
    return ''


def time_ago(timestamp):
    """Turns a time into wording like '12 minutes ago'."""
    seconds = max(0, int(time.time()) - int(timestamp))
    if seconds < 60:
        return 'just now'
    for size, unit in ((86400, 'day'), (3600, 'hour'), (60, 'minute')):
        if seconds >= size:
            count = seconds // size
            return f"{count} {unit}{'' if count == 1 else 's'} ago"


def add_meter(items):
    """Adds each item's plays as a percentage of the most-played item."""
    highest = max([item['scrobbles'] for item in items] or [1]) or 1
    for item in items:
        item['meter'] = max(3, round(item['scrobbles'] / highest * 100))
    return items


def load_week_scrobbles():
    """Counts my scrobbles over the last 7 days."""
    one_week_ago = int(time.time()) - 7 * 24 * 60 * 60
    answer = lastfm_get('user.getrecenttracks', limit=1, **{'from': one_week_ago})
    total = int(answer['recenttracks']['@attr']['total'])
    return f"{total:,} song{'' if total == 1 else 's'} played in the last week"


def load_recent():
    tracks = as_list(lastfm_get('user.getrecenttracks', limit=6)['recenttracks'].get('track'))
    now_playing = None
    recent = []
    for track in tracks:
        item = {
            'title': track.get('name', ''),
            'artist': track.get('artist', {}).get('#text', ''),
            'album': track.get('album', {}).get('#text', ''),
            'image': best_image(track),
            'url': track.get('url', ''),
        }
        if track.get('@attr', {}).get('nowplaying') == 'true':
            now_playing = item
        else:
            item['date'] = time_ago(track['date']['uts'])
            recent.append(item)
    return {'now_playing': now_playing, 'recent_tracks': recent[:5]}


def load_top_artists():
    artists = as_list(lastfm_get('user.gettopartists', period='overall', limit=10)['topartists'].get('artist'))
    return add_meter([
        {'name': a['name'], 'scrobbles': int(a['playcount']), 'url': a.get('url', '')}
        for a in artists
    ])


def load_top_tracks():
    tracks = as_list(lastfm_get('user.gettoptracks', period='12month', limit=10)['toptracks'].get('track'))
    return add_meter([
        {
            'title': t['name'],
            'artist': t.get('artist', {}).get('name', ''),
            'scrobbles': int(t['playcount']),
            'url': t.get('url', ''),
        }
        for t in tracks
    ])


def load_top_albums(period):
    albums = as_list(lastfm_get('user.gettopalbums', period=period, limit=10)['topalbums'].get('album'))
    return [
        {
            'title': a['name'],
            'artist': a.get('artist', {}).get('name', ''),
            'scrobbles': int(a['playcount']),
            'image': best_image(a),
            'url': a.get('url', ''),
        }
        for a in albums
    ]


def load_lately_artists():
    """My most-played artists over the last month."""
    artists = lastfm_get('user.gettopartists', period='1month', limit=LATELY_TOP_ARTISTS)['topartists']
    return [
        {'name': a['name'], 'scrobbles': int(a['playcount'])}
        for a in as_list(artists.get('artist'))
    ]


def find_artist_lately(names):
    """Returns the artist's name if I've been playing them a lot lately."""
    wanted = {name.strip().lower() for name in names}
    for artist in cached('artists lately', 600, load_lately_artists, []):
        if artist['name'].lower() in wanted and artist['scrobbles'] >= LATELY_MIN_SCROBBLES:
            return artist['name']
    return None


def load_artist_art():
    """Uses each artist's most-played album cover as their picture."""
    albums = as_list(lastfm_get('user.gettopalbums', period='overall', limit=500)['topalbums'].get('album'))
    art = {}
    for album in albums:
        artist = album.get('artist', {}).get('name', '').lower()
        image = best_image(album)
        if artist and image and artist not in art:
            art[artist] = image
    return art


def get_artist_art():
    return cached('artist art', 3600, load_artist_art, {})


def get_lastfm_stats():
    """Fetches all necessary Last.fm data for the dashboard."""
    stats_data = {'username': LASTFM_USERNAME, 'name': DISPLAY_NAME}
    stats_data['week_scrobbles'] = cached('week scrobbles', 600, load_week_scrobbles, '')
    stats_data.update(cached('recent tracks', 30, load_recent, {'now_playing': None, 'recent_tracks': []}))

    artist_art = get_artist_art()
    top_artists = cached('top artists', 600, load_top_artists, [])
    stats_data['top_artists'] = [
        dict(artist, image=artist_art.get(artist['name'].lower(), '')) for artist in top_artists
    ]
    stats_data['top_tracks'] = cached('top tracks', 600, load_top_tracks, [])
    stats_data['month_albums'] = cached('albums this month', 600, lambda: load_top_albums('1month'), [])
    stats_data['top_albums'] = cached('albums this year', 600, lambda: load_top_albums('12month'), [])

    # The banner shows the current track, or the last one played
    recent = stats_data['recent_tracks']
    stats_data['hero'] = stats_data['now_playing'] or (recent[0] if recent else None)
    return stats_data


def load_artist_plays(period):
    """Gets everyone I played during a period, as {artist name: plays}."""
    plays = {}
    page = 1
    while True:
        top_artists = lastfm_get('user.gettopartists', period=period, limit=1000, page=page)['topartists']
        for artist in as_list(top_artists.get('artist')):
            plays[artist['name'].lower()] = int(artist['playcount'])
        if page >= int(top_artists['@attr']['totalPages']):
            return plays
        page += 1


def get_artist_plays(period):
    """Returns None if Last.fm couldn't answer, so no tag is added by mistake."""
    return cached(f'artist plays {period}', 600, lambda: load_artist_plays(period), None)


def timing_badges(artist_name, all_time_plays):
    """Adds tags based on when I played an artist."""
    badges = []
    key = artist_name.lower()

    discovered_plays = get_artist_plays(DISCOVERED_PERIOD)
    if (discovered_plays is not None and all_time_plays >= DISCOVERED_MIN_PLAYS
            and discovered_plays.get(key, 0) >= 0.9 * all_time_plays):
        badges.append('Recently discovered')

    not_played_plays = get_artist_plays(NOT_PLAYED_PERIOD)
    if not_played_plays is not None and key not in not_played_plays:
        badges.append("Haven't played in a while")

    return badges


def find_artist_in_my_history(names):
    """Looks through my all-time artists, most played first, for any of these names."""
    wanted = {name.strip().lower() for name in names}
    page = 1

    while True:
        top_artists = lastfm_get('user.gettopartists', period='overall', limit=1000, page=page)['topartists']

        for position, artist in enumerate(as_list(top_artists.get('artist')), start=1):
            if artist['name'].lower() in wanted:
                rank = (page - 1) * 1000 + position
                return artist['name'], rank, int(artist['playcount'])

        if page >= int(top_artists['@attr']['totalPages']):
            return None, None, 0
        page += 1


def describe_listening(artist_name, rank):
    """Turns an artist's all-time rank into a friendly answer."""
    if rank <= 25:
        return f"Yes! {artist_name} is one of my favorite artists."
    if rank <= 50:
        return f"Yes, I've listened to {artist_name} and I like them."
    if rank <= 100:
        return f"Yes, I've listened to {artist_name} before."
    return f"Yes, but I don't listen to {artist_name} much."


def listening_badge(rank):
    """A short label shown beside the search answer."""
    if rank <= 25:
        return 'Favorite'
    if rank <= 50:
        return 'Likes them'
    if rank <= 100:
        return 'Heard before'
    return None


@app.route('/', methods=['GET', 'POST'])
def index():
    # 1. Fetch general dashboard stats
    data = get_lastfm_stats()
    search = None

    # 2. Handle the "Have I listened to..." search bar logic
    artist_query = request.args.get('artist_name', '').strip()
    if artist_query:
        try:
            network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET)

            # Find the official artist name, which also helps with small typos
            results = network.search_for_artist(artist_query).get_next_page()
            names_to_check = [artist_query]
            if results:
                names_to_check.append(results[0].get_name())

            # First check whether I've been playing this artist a lot lately
            lately_artist = find_artist_lately(names_to_check)

            # Also look for the typed or official name in my all-time history
            my_artist, rank, all_time_plays = find_artist_in_my_history(names_to_check)

            if lately_artist:
                # An all-time favorite keeps its Favorite badge beside Heavy rotation
                badges = ['Heavy rotation']
                if rank and listening_badge(rank) == 'Favorite':
                    badges.insert(0, 'Favorite')
                if my_artist:
                    badges += timing_badges(my_artist, all_time_plays)
                search = {
                    'text': f"Yes, I've been listening to {lately_artist} a lot lately!",
                    'badges': badges,
                    'image': get_artist_art().get(lately_artist.lower(), ''),
                    'found': True,
                }
            elif my_artist:
                rank_badge = listening_badge(rank)
                badges = [rank_badge] if rank_badge else []
                badges += timing_badges(my_artist, all_time_plays)
                search = {
                    'text': describe_listening(my_artist, rank),
                    'badges': badges,
                    'image': get_artist_art().get(my_artist.lower(), ''),
                    'found': True,
                }
            elif results:
                search = {
                    'text': f"Nope, I haven't listened to {results[0].get_name()} yet.",
                    'badges': ['Recommend it to me'],
                }
            else:
                search = {'text': f"Could not find an artist named '{artist_query}'. Check the spelling and try again."}

        except Exception as e:
            print(f"Search Error: {e}", flush=True)
            search = {'text': "That search didn't go through. Try again in a minute."}

    return render_template('stats.html', data=data, search=search, artist_query=artist_query, badge_definitions=BADGE_DEFINITIONS)


if __name__ == '__main__':
    app.run(debug=True)
