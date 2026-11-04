"""Download the character portraits used by the site's character picker.

The portraits come from the Don't Starve wiki (and the Uncompromising Mode wiki
for the mod's exclusive characters) and are committed under ``site/portraits``.
Running this script is only necessary when a character is added or a portrait
changes.

Usage::

    py tools/fetch_portraits.py
    py tools/fetch_portraits.py --force Wilson Willow

Only the standard library and Pillow are required.
"""

from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PORTRAIT_DIR = ROOT / "site" / "portraits"
USER_AGENT = "DSTMeta/0.1 (local food planner; portrait downloader)"

# Display name -> wiki image URL.  The file name is the lower-case slug.
CHARACTERS = {
    "Wilson": "https://dontstarve.wiki.gg/images/Wilson_Portrait.png",
    "Willow": "https://dontstarve.wiki.gg/images/Willow_Portrait.png",
    "Wolfgang": "https://dontstarve.wiki.gg/images/Wolfgang_Portrait.png",
    "Wendy": "https://dontstarve.wiki.gg/images/Wendy_Portrait.png",
    "WX-78": "https://dontstarve.wiki.gg/images/WX-78_Portrait.png",
    "Wickerbottom": "https://dontstarve.wiki.gg/images/Wickerbottom_Portrait.png",
    "Woodie": "https://dontstarve.wiki.gg/images/Woodie_Portrait.png",
    "Wes": "https://dontstarve.wiki.gg/images/Wes_Portrait.png",
    "Maxwell": "https://dontstarve.wiki.gg/images/Maxwell_Portrait.png",
    "Wigfrid": "https://dontstarve.wiki.gg/images/Wigfrid_Portrait.png",
    "Webber": "https://dontstarve.wiki.gg/images/Webber_Portrait.png",
    "Winona": "https://dontstarve.wiki.gg/images/Winona_Portrait.png",
    "Warly": "https://dontstarve.wiki.gg/images/Warly_Portrait.png",
    "Walter": "https://dontstarve.wiki.gg/images/Walter_Portrait.png",
    "Wortox": "https://dontstarve.wiki.gg/images/Wortox_Portrait.png",
    "Wormwood": "https://dontstarve.wiki.gg/images/Wormwood_Portrait.png",
    "Wurt": "https://dontstarve.wiki.gg/images/Wurt_Portrait.png",
    "Wanda": "https://dontstarve.wiki.gg/images/Wanda_Portrait.png",
    "Wonkey": "https://dontstarve.wiki.gg/images/Wonkey_Portrait.png",
    # Uncompromising Mode exclusives.
    "Winky": "https://uncompromisingmode.wiki.gg/images/Winky_Portrait.png",
    "Wathom": "https://uncompromisingmode.wiki.gg/images/Wathom_Portrait.png",
    "Wixie": "https://uncompromisingmode.wiki.gg/images/Wixie_Portrait.png",
}


def slug(name: str) -> str:
    """Return the file name (without extension) used for one portrait."""
    return "".join(
        character if character.isalnum() else "-" for character in name.lower()
    ).strip("-")


def download(url: str) -> bytes:
    host = (
        "uncompromisingmode.wiki.gg"
        if "uncompromisingmode" in url
        else "dontstarve.wiki.gg"
    )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": f"https://{host}/",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def portrait(data: bytes) -> bytes:
    """Validate the PNG and save it unchanged so portraits stay consistent."""
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="only refresh these characters")
    parser.add_argument("--force", action="store_true", help="replace existing files")
    args = parser.parse_args()

    wanted = list(dict.fromkeys(args.names or CHARACTERS))
    unknown = sorted(set(wanted) - set(CHARACTERS))
    if unknown:
        parser.error(f"unknown characters: {', '.join(unknown)}")

    PORTRAIT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for name in wanted:
        path = PORTRAIT_DIR / f"{slug(name)}.png"
        if path.exists() and not args.force:
            continue
        raw = portrait(download(CHARACTERS[name]))
        path.write_bytes(raw)
        written += 1
        print(f"portrait {name} -> {path.name}")

    missing = [
        name for name in CHARACTERS if not (PORTRAIT_DIR / f"{slug(name)}.png").exists()
    ]
    print(
        f"\n{len(CHARACTERS) - len(missing)}/{len(CHARACTERS)} portraits present "
        f"({written} written)"
    )
    if missing:
        print("missing:", ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
