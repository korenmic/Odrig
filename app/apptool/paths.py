"""Where things are: the repository and the web code."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "app"
WWW = APP / "www"
