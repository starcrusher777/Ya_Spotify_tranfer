"""CLI entry: sync Spotify ↔ Yandex Music. Configure constants below or use the GUI app."""
from transfer_core import run_sync

SPOTIPY_CLIENT_ID = ""
SPOTIPY_CLIENT_SECRET = ""
SPOTIPY_REDIRECT_URI = ""
YANDEX_USER_ID = ""
YANDEX_COOKIES = ""


if __name__ == "__main__":
    run_sync(
        SPOTIPY_CLIENT_ID,
        SPOTIPY_CLIENT_SECRET,
        SPOTIPY_REDIRECT_URI,
        YANDEX_USER_ID,
        YANDEX_COOKIES,
    )
