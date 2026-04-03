# Spotify ↔ Yandex Music Transfer

Sync liked tracks between **Spotify** and **Yandex Music** using fuzzy matching: Spotify saved library ↔ Yandex “heart” (likes).

## Features

- **Two-way sync**: Spotify → Yandex likes and Yandex → Spotify saved tracks.
- **Windows app** (`SpotifyYandexTransfer.exe`): GUI for credentials, log output, settings saved under `%LOCALAPPDATA%\YaSpotifyTransfer\`.
- **CLI** (`transfer_script.py`): same logic, configure constants in the file.

## Download (Windows)

Pre-built **64-bit Windows** executable is attached to the repo’s **Releases** page when a maintainer publishes a version tag (see [Releasing](#releasing) below).

## Requirements (from source)

- Python 3.9+
- Dependencies: see `requirements.txt`

## Spotify setup

1. Open [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Create an app; copy **Client ID** and **Client Secret**.
3. Add **Redirect URI** (e.g. `http://localhost:8888/callback`) and save.

## Yandex Music setup

1. Open [Yandex Music](https://music.yandex.ru) in a browser (logged in).
2. Open DevTools → **Network**, trigger any action (e.g. like a track).
3. Copy **Cookie** from a request header and your **user ID** (e.g. from header `x-yandex-music-multi-auth-user-id` or your profile).

## Run the Windows app (source)

```bash
pip install -r requirements.txt
python app_gui.py
```

On first sync, Spotify opens the browser for login. OAuth token is stored under `%LOCALAPPDATA%\YaSpotifyTransfer\.spotify_token_cache`.

## Run the CLI

1. Edit `transfer_script.py` and set `SPOTIPY_*` and `YANDEX_*` variables.
2. Run:

```bash
pip install -r requirements.txt
python transfer_script.py
```

## Build Windows `.exe` locally

```bat
build_windows.bat
```

Or manually:

```bash
pip install -r requirements.txt -r requirements-build.txt
pyinstaller --noconfirm SpotifyYandexTransfer.spec
```

Output: `dist\SpotifyYandexTransfer.exe` (one file, no console window; logs appear in the app).

## Security note

**Yandex cookies** and **Spotify secrets** are sensitive. The GUI can save them to `%LOCALAPPDATA%\YaSpotifyTransfer\config.json`. Do not share that file or commit it to git.

## License

MIT — see [LICENSE](LICENSE).
