import os
import time
import requests
from fuzzywuzzy import fuzz
import spotipy
from spotipy.oauth2 import SpotifyOAuth

#Config
SPOTIFY_SCOPE = "user-library-read user-library-modify"
FUZZY_THRESHOLD = 80

SPOTIPY_CLIENT_ID = ''
SPOTIPY_CLIENT_SECRET = ''
SPOTIPY_REDIRECT_URI = ''
YANDEX_USER_ID = ''
YANDEX_COOKIES = ''


YANDEX_BASE = "https://api.music.yandex.ru"

# === Spotify Initialization  ===
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SPOTIFY_SCOPE,
    open_browser=True
))

# === Yandex Cookies ===
def make_yandex_session():
    session = requests.Session()
    for pair in YANDEX_COOKIES.split(";"):
        if "=" in pair:
            name, val = pair.strip().split("=", 1)
            session.cookies.set(name, val)
    session.headers.update({
        "accept": "*/*",
        "accept-language": "ru",
        "origin": "https://music.yandex.ru",
        "referer": "https://music.yandex.ru/",
        "x-requested-with": "XMLHttpRequest",
        "x-yandex-music-client": "YandexMusicWebNext/1.0.0",
        "x-yandex-music-multi-auth-user-id": YANDEX_USER_ID,
        "x-yandex-music-without-invocation-info": "1",
        "x-retpath-y": "https://music.yandex.ru/collection",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    return session

# === Spotify helpers ===
def get_spotify_saved_tracks():
    tracks = []
    saved_ids = set()
    results = sp.current_user_saved_tracks(limit=50)
    while results:
        for item in results["items"]:
            track = item["track"]
            artist = track["artists"][0]["name"] if track["artists"] else ""
            title = track["name"]
            tracks.append((artist, title))
            saved_ids.add(track["id"])
        if results.get("next"):
            results = sp.next(results)
        else:
            break
    return tracks, saved_ids

def add_track_to_spotify(track_id):
    try:
        sp.current_user_saved_tracks_add([track_id])
        return True
    except Exception as e:
        print("  [Ошибка →Spotify]", e)
        return False

def find_spotify_track(artist, title):
    query = f"{artist} {title}"
    results = sp.search(q=query, type="track", limit=5)
    for track in results.get("tracks", {}).get("items", []):
        sp_artist = track["artists"][0]["name"] if track["artists"] else ""
        sp_title = track["name"]
        similarity = fuzz.ratio(f"{artist} {title}", f"{sp_artist} {sp_title}")
        if similarity >= FUZZY_THRESHOLD:
            return track["id"]
    return None

# === Ya helpers ===
def get_yandex_liked_tracks(session):
    tracks = []
    liked_ids = set()
    resp = session.get(f"{YANDEX_BASE}/users/{YANDEX_USER_ID}/likes/tracks", params={"limit": 100, "offset": 0})
    resp.raise_for_status()
    data = resp.json()
    library = data.get("library", {})
    raw = library.get("tracks", [])
    for item in raw:
        tid = item.get("id")
        aid = item.get("albumId") or item.get("album_id")
        if not tid:
            continue
        tr = session.get(f"{YANDEX_BASE}/tracks/{tid}")
        if not tr.ok:
            continue
        trj = tr.json()
        if isinstance(trj, list) and trj:
            trj = trj[0]
        track_obj = (trj.get("track") or trj) if isinstance(trj, dict) else {}
        artist = ""
        if track_obj.get("artists"):
            artist = track_obj["artists"][0].get("name", "")
        title = track_obj.get("title", "")
        tracks.append((artist, title))
        liked_ids.add(str(tid))
    return list(reversed(tracks)), liked_ids

def find_yandex_track(session, artist, title):
    query = f"{artist} {title}"
    params = {"text": query, "type": "track", "pagesize": 5}
    resp = session.get(f"{YANDEX_BASE}/search", params=params)
    if not resp.ok:
        return None, None
    results = resp.json().get("tracks", {}).get("results", [])
    for track in results:
        ya_artist = ""
        if track.get("artists"):
            ya_artist = track["artists"][0].get("name", "")
        ya_title = track.get("title", "")
        similarity = fuzz.ratio(f"{artist} {title}", f"{ya_artist} {ya_title}")
        if similarity >= FUZZY_THRESHOLD:
            return track.get("id"), track.get("albumId") or track.get("album_id")
    return None, None

def add_to_yandex_likes(session, track_id, album_id):
    url = f"{YANDEX_BASE}/users/{YANDEX_USER_ID}/likes/tracks/{track_id}:{album_id}/add"
    r = session.post(url)
    return r.ok

# === Sync ===
def sync():
    y_session = make_yandex_session()

    spotify_tracks, spotify_ids = get_spotify_saved_tracks()
    print(f"[Spotify] сохранённых: {len(spotify_tracks)}")

    yandex_tracks, yandex_ids = get_yandex_liked_tracks(y_session)
    print(f"[Yandex] лайкнутых: {len(yandex_tracks)}")

    # Spotify -> Yandex
    for artist, title in spotify_tracks:
        if (artist, title) in yandex_tracks:
            continue
        yid, y_album = find_yandex_track(y_session, artist, title)
        if not yid or not y_album:
            continue
        if yid not in yandex_ids:
            ok = add_to_yandex_likes(y_session, yid, y_album)
            if ok:
                print(f"[→Yandex] Лайкнуто: {artist} - {title}")
                yandex_ids.add(yid)
            else:
                print(f"[Ошибка →Yandex] Не удалось лайкнуть: {artist} - {title}")
        time.sleep(1)

    # Yandex -> Spotify
    for artist, title in yandex_tracks:
        if (artist, title) in spotify_tracks:
            continue
        sid = find_spotify_track(artist, title)
        if sid and sid not in spotify_ids:
            if add_track_to_spotify(sid):
                print(f"[→Spotify] Сохранено: {artist} - {title}")
                spotify_ids.add(sid)
            else:
                print(f"[Ошибка →Spotify] {artist} - {title}")
        time.sleep(1)


if __name__ == "__main__":
    sync()