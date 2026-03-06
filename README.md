# Spotify ↔ Yandex Music Transfer

Script for syncing liked/saved tracks between Spotify and Yandex Music. Copies tracks from Spotify to Yandex and from Yandex to Spotify using fuzzy matching.

## Requirements

- Python 3
- `fuzzywuzzy`, `spotipy`, `python-Levenshtein`

## Setup

1. **Spotify**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
   - Create an app and get **Client ID** and **Client Secret**.
   - Set **Redirect URI** (e.g. `http://localhost:8888/callback`).

2. **Yandex Music**
   - Open [Yandex Music](https://music.yandex.ru) in a browser.
   - Open DevTools → Network, perform any action (e.g. like a track).
   - Copy **cookies** from request headers and your **user ID** (e.g. from `x-yandex-music-multi-auth-user-id` or user profile).

3. **Config**
   - Edit `transfer_script.py`: fill in `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, `SPOTIPY_REDIRECT_URI`, `YANDEX_USER_ID`, `YANDEX_COOKIES`.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python transfer_script.py
```

On first run, Spotify will open a browser for authorization.
