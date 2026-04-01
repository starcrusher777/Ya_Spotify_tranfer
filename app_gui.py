"""Windows GUI for Spotify ↔ Yandex Music sync."""
from __future__ import annotations

import json
import os
import pathlib
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from transfer_core import run_sync

APP_DIR_NAME = "YaSpotifyTransfer"
CONFIG_NAME = "config.json"


def app_data_dir() -> pathlib.Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.path.expanduser("~/.local/share")
    d = pathlib.Path(base) / APP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> pathlib.Path:
    return app_data_dir() / CONFIG_NAME


def load_config() -> dict:
    p = config_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    config_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class TransferApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Spotify ↔ Yandex Music Transfer")
        self.minsize(560, 520)
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._worker: threading.Thread | None = None

        cfg = load_config()

        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Spotify Client ID").grid(row=0, column=0, sticky=tk.W, **pad)
        self.var_client_id = tk.StringVar(value=cfg.get("spotify_client_id", ""))
        ttk.Entry(frm, textvariable=self.var_client_id, width=56).grid(
            row=0, column=1, sticky=tk.EW, **pad
        )

        ttk.Label(frm, text="Spotify Client Secret").grid(row=1, column=0, sticky=tk.W, **pad)
        self.var_client_secret = tk.StringVar(value=cfg.get("spotify_client_secret", ""))
        ttk.Entry(frm, textvariable=self.var_client_secret, width=56, show="*").grid(
            row=1, column=1, sticky=tk.EW, **pad
        )

        ttk.Label(frm, text="Spotify Redirect URI").grid(row=2, column=0, sticky=tk.W, **pad)
        self.var_redirect = tk.StringVar(
            value=cfg.get("spotify_redirect_uri", "http://localhost:8888/callback")
        )
        ttk.Entry(frm, textvariable=self.var_redirect, width=56).grid(
            row=2, column=1, sticky=tk.EW, **pad
        )

        ttk.Label(frm, text="Yandex User ID").grid(row=3, column=0, sticky=tk.W, **pad)
        self.var_ya_uid = tk.StringVar(value=cfg.get("yandex_user_id", ""))
        ttk.Entry(frm, textvariable=self.var_ya_uid, width=56).grid(
            row=3, column=1, sticky=tk.EW, **pad
        )

        ttk.Label(frm, text="Yandex cookies (header string)").grid(row=4, column=0, sticky=tk.NW, **pad)
        self.txt_cookies = scrolledtext.ScrolledText(frm, width=56, height=5, wrap=tk.WORD)
        self.txt_cookies.grid(row=4, column=1, sticky=tk.EW, **pad)
        self.txt_cookies.insert("1.0", cfg.get("yandex_cookies", ""))

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=5, column=0, columnspan=2, pady=8)
        self.btn_run = ttk.Button(btn_row, text="Start sync", command=self._on_sync)
        self.btn_run.pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Save settings", command=self._save_settings).pack(
            side=tk.LEFT, padx=4
        )

        ttk.Label(frm, text="Log").grid(row=6, column=0, sticky=tk.NW, **pad)
        self.txt_log = scrolledtext.ScrolledText(frm, width=56, height=16, state=tk.DISABLED)
        self.txt_log.grid(row=6, column=1, sticky=tk.NSEW, **pad)

        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(6, weight=1)

        self.after(200, self._drain_log_queue)

    def _append_log(self, line: str) -> None:
        self.txt_log.configure(state=tk.NORMAL)
        self.txt_log.insert(tk.END, line + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.configure(state=tk.DISABLED)

    def _drain_log_queue(self) -> None:
        try:
            while True:
                msg = self._log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        self.after(200, self._drain_log_queue)

    def _log(self, msg: str) -> None:
        self._log_queue.put(msg)

    def _get_cookies(self) -> str:
        return self.txt_cookies.get("1.0", tk.END).strip()

    def _save_settings(self) -> None:
        save_config(
            {
                "spotify_client_id": self.var_client_id.get().strip(),
                "spotify_client_secret": self.var_client_secret.get().strip(),
                "spotify_redirect_uri": self.var_redirect.get().strip(),
                "yandex_user_id": self.var_ya_uid.get().strip(),
                "yandex_cookies": self._get_cookies(),
            }
        )
        messagebox.showinfo("Settings", "Saved to:\n" + str(config_path()))

    def _on_sync(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "Sync is already running.")
            return

        cid = self.var_client_id.get().strip()
        secret = self.var_client_secret.get().strip()
        redir = self.var_redirect.get().strip()
        yuid = self.var_ya_uid.get().strip()
        cookies = self._get_cookies()

        if not all([cid, secret, redir, yuid, cookies]):
            messagebox.showerror(
                "Missing fields",
                "Fill in Spotify credentials, redirect URI, Yandex user ID, and cookies.",
            )
            return

        self._append_log("--- Starting sync ---")
        self.btn_run.configure(state=tk.DISABLED)

        def work() -> None:
            try:
                run_sync(cid, secret, redir, yuid, cookies, log=self._log)
                self._log("--- Done ---")
            except Exception as e:
                self._log(f"[Error] {e!r}")
            finally:
                self.after(0, lambda: self.btn_run.configure(state=tk.NORMAL))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()


def main() -> None:
    app = TransferApp()
    app.mainloop()


if __name__ == "__main__":
    main()
