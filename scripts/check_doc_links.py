"""Check external Markdown links using only the Python standard library."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\((https?://[^\s)]+)\)|<(https?://[^\s>]+)>")


def check_url(url: str) -> tuple[str, str | None]:
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "HPS-documentation-link-check/1.0"})
            with urlopen(request, timeout=20) as response:
                if response.status < 400:
                    return url, None
                return url, f"HTTP {response.status}"
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt == 2:
                return url, str(exc)
            time.sleep(attempt + 1)
    return url, "Request did not complete"


def main() -> int:
    sources: dict[str, set[str]] = {}
    files = [*sorted((ROOT / "docs").rglob("*.md"))]
    files.extend(ROOT / name for name in ("README.md", "CONTRIBUTING.md", "RELEASING.md"))
    for path in files:
        for match in LINK.finditer(path.read_text(encoding="utf-8")):
            url = urldefrag(match.group(1) or match.group(2))[0]
            sources.setdefault(url, set()).add(path.relative_to(ROOT).as_posix())
    failures = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for url, error in pool.map(check_url, sorted(sources)):
            if error:
                failures += 1
                print(f"FAIL {url}: {error} ({', '.join(sorted(sources[url]))})")
    print(f"Checked {len(sources)} external URLs; {failures} failures.")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
