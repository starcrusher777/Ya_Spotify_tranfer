"""Shared sync logic for CLI and GUI."""
from __future__ import annotations

import os
import pathlib
import sys
import time
from collections.abc import Callable
from typing import Optional

import requests
import spotipy
from fuzzywuzzy import fuzz
from spotipy.oauth2 import SpotifyOAuth

SPOTIFY_SCOPE = "user-library-read user-library-modify"
FUZZY_THRESHOLD = 80
YANDEX_BASE = "https://api.music.yandex.ru"

LogFn = Callable[[str], None]


def _default_log(msg: str) -> None:
    print(msg)


def spotify_token_cache_path() -> str:
    """Persist OAuth token next to app config on Windows / beside cwd otherwise."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        d = pathlib.Path(base) / "YaSpotifyTransfer"
        d.mkdir(parents=True, exist_ok=True)
        return str(d / ".spotify_token_cache")
    return ".spotify_token_cache"


def create_spotify_client(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> spotipy.Spotify:
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=SPOTIFY_SCOPE,
            open_browser=True,
            cache_path=spotify_token_cache_path(),
        )
    )


def make_yandex_session(yandex_user_id: str, yandex_cookies: str) -> requests.Session:
    session = requests.Session()
    for pair in yandex_cookies.split(";"):
        if "=" in pair:
            name, val = pair.strip().split("=", 1)
            session.cookies.set(name, val)
    session.headers.update(
        {
            "accept": "*/*",
            "accept-language": "ru",
            "origin": "https://music.yandex.ru",
            "referer": "https://music.yandex.ru/",
            "x-requested-with": "XMLHttpRequest",
            "x-yandex-music-client": "YandexMusicWebNext/1.0.0",
            "x-yandex-music-multi-auth-user-id": yandex_user_id,
            "x-yandex-music-without-invocation-info": "1",
            "x-retpath-y": "https://music.yandex.ru/collection",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
    )
    return session


def get_spotify_saved_tracks(sp: spotipy.Spotify):
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


def add_track_to_spotify(sp: spotipy.Spotify, track_id: str, log: LogFn) -> bool:
    try:
        sp.current_user_saved_tracks_add([track_id])
        return True
    except Exception as e:
        log(f"  [Error →Spotify] {e}")
        return False


def find_spotify_track(sp: spotipy.Spotify, artist: str, title: str) -> Optional[str]:
    query = f"{artist} {title}"
    results = sp.search(q=query, type="track", limit=5)
    for track in results.get("tracks", {}).get("items", []):
        sp_artist = track["artists"][0]["name"] if track["artists"] else ""
        sp_title = track["name"]
        similarity = fuzz.ratio(f"{artist} {title}", f"{sp_artist} {sp_title}")
        if similarity >= FUZZY_THRESHOLD:
            return track["id"]
    return None


def get_yandex_liked_tracks(session: requests.Session, yandex_user_id: str):
    tracks = []
    liked_ids = set()
    resp = session.get(
        f"{YANDEX_BASE}/users/{yandex_user_id}/likes/tracks",
        params={"limit": 100, "offset": 0},
    )
    resp.raise_for_status()
    data = resp.json()
    library = data.get("library", {})
    raw = library.get("tracks", [])
    for item in raw:
        tid = item.get("id")
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


def find_yandex_track(session: requests.Session, artist: str, title: str):
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


def add_to_yandex_likes(
    session: requests.Session, yandex_user_id: str, track_id, album_id
) -> bool:
    url = (
        f"{YANDEX_BASE}/users/{yandex_user_id}/likes/tracks/"
        f"{track_id}:{album_id}/add"
    )
    r = session.post(url)
    return r.ok


def run_sync(
    spotify_client_id: str,
    spotify_client_secret: str,
    spotify_redirect_uri: str,
    yandex_user_id: str,
    yandex_cookies: str,
    log: Optional[LogFn] = None,
) -> None:
    log = log or _default_log
    sp = create_spotify_client(
        spotify_client_id,
        spotify_client_secret,
        spotify_redirect_uri,
    )
    y_session = make_yandex_session(yandex_user_id, yandex_cookies)

    spotify_tracks, spotify_ids = get_spotify_saved_tracks(sp)
    log(f"[Spotify] saved: {len(spotify_tracks)}")

    yandex_tracks, yandex_ids = get_yandex_liked_tracks(y_session, yandex_user_id)
    log(f"[Yandex] liked: {len(yandex_tracks)}")

    for artist, title in spotify_tracks:
        if (artist, title) in yandex_tracks:
            continue
        yid, y_album = find_yandex_track(y_session, artist, title)
        if not yid or not y_album:
            continue
        if str(yid) not in yandex_ids:
            ok = add_to_yandex_likes(y_session, yandex_user_id, yid, y_album)
            if ok:
                log(f"[→Yandex] Liked: {artist} - {title}")
                yandex_ids.add(str(yid))
            else:
                log(f"[Error →Yandex] Failed to like: {artist} - {title}")
        time.sleep(1)

    for artist, title in yandex_tracks:
        if (artist, title) in spotify_tracks:
            continue
        sid = find_spotify_track(sp, artist, title)
        if sid and sid not in spotify_ids:
            if add_track_to_spotify(sp, sid, log):
                log(f"[→Spotify] Saved: {artist} - {title}")
                spotify_ids.add(sid)
            else:
                log(f"[Error →Spotify] {artist} - {title}")
        time.sleep(1)
