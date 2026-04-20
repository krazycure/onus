"""Custom AceStep UI -- Client-side JavaScript.

Exports:
    CLIENT_JS: The full JavaScript for the main interface page.

See Also:
    custom_interface.py      - Backend core (init, generate, CLI)
    custom_interface_css.py  - Stylesheet (STYLES_CSS)
    custom_interface_html.py - HTML body template (FRONTEND_BODY_HTML)
    custom_interface_routes.py - API routes + FastAPI app

Chunk files are stored as plain text to avoid triple-quote escaping issues.
"""

import os

_CHUNK_DIR = os.path.dirname(__file__)


def _read_chunk(name: str) -> str:
    with open(os.path.join(_CHUNK_DIR, name), "r") as f:
        return f.read()


CLIENT_JS = _read_chunk("js_modes.js") + _read_chunk("js_results.js") + _read_chunk("js_settings.js")
