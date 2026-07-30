import re
from .models import Airport
from .client import fetch_airports_js


JS_OBJECT_RE = re.compile(r"var\s+airportsArray\s*=\s*(\{.*?\});", re.DOTALL)
ENTRY_RE = re.compile(r'"([A-Z0-9]{3})"\s*:\s*"([^"]*)"')


class AirportDB:
    def __init__(self):
        self._airports: dict[str, str] = {}
        self._loaded = False

    async def _ensure_loaded(self):
        if self._loaded:
            return
        js = await fetch_airports_js()
        self._airports = parse_airports_js(js)
        self._loaded = True

    async def search(self, query: str) -> list[Airport]:
        await self._ensure_loaded()
        q = query.strip().upper()
        results = []
        for code, name in self._airports.items():
            if q == code:
                return [Airport(code=code, name=name)]
            if q in name.upper() or (len(q) >= 2 and q in code):
                results.append(Airport(code=code, name=name))
        results.sort(key=lambda a: (0 if a.name.upper().startswith(q) or a.code.startswith(q) else 1, a.name))
        return results[:50]

    async def get_name(self, code: str) -> str | None:
        await self._ensure_loaded()
        return self._airports.get(code.upper())


def parse_airports_js(js: str) -> dict[str, str]:
    m = JS_OBJECT_RE.search(js)
    if not m:
        return {}
    airports: dict[str, str] = {}
    for code, name in ENTRY_RE.findall(m.group(1)):
        airports[code] = name
    return airports
