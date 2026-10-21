"""Download Manage2Sail entries into season files."""

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


EVENT_LINK_PATTERN = re.compile(r'href="/en-US/event/([0-9a-f-]+)"[^>]*>([^<]+)')
BOOTSTRAP_PATTERN = re.compile(r"window\.boostrapedResourceData = (\{.*?\});")
LEAGUE_NAME_PATTERN = re.compile(r"^(\d+)\.")


def _get_text(url):
    request = Request(url, headers={"User-Agent": "liga-insights downloader"})
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def _normalise(value):
    value = unicodedata.normalize("NFKD", html.unescape(value or ""))
    value = value.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", value)


def _overview_url(url, year):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["year"] = str(year)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _event_links(overview_url, year):
    overview = _get_text(_overview_url(overview_url, year))
    return [
        (event_id, html.unescape(title))
        for event_id, title in EVENT_LINK_PATTERN.findall(overview)
        if "Pokal" not in html.unescape(title)
        and "Saison" not in html.unescape(title)
        and "Women on Water" not in html.unescape(title)
    ]


def _event_classes(event_id, base_url):
    page = _get_text(f"{base_url}/en-US/event/{event_id}")
    match = BOOTSTRAP_PATTERN.search(page)
    if match is None:
        raise ValueError(f"Could not find league classes on event {event_id}")
    return json.loads(match.group(1))["Regatta"]


def _club_id(entry, clubs):
    name_values = (
        entry.get("ClubName"),
        entry.get("BoatName"),
        entry.get("TeamName"),
    )
    normalised_values = [_normalise(value) for value in name_values if value]
    long_candidates = []
    for club_id, club in clubs.items():
        name = _normalise(club["long"])
        if any(len(name) >= 4 and (name in source or source in name) for source in normalised_values):
            long_candidates.append(club_id)

    if len(set(long_candidates)) == 1:
        return long_candidates[0]

    candidates = []
    for club_id, club in clubs.items():
        name = _normalise(club["short"])
        if any(len(name) >= 4 and name == source for source in normalised_values):
            candidates.append(club_id)

    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        code = _normalise(entry.get("ClubCode"))
        code_candidates = [
            club_id
            for club_id, club in clubs.items()
            if code in {_normalise(club["short"]), _normalise(club["long"])}
        ]
        if len(code_candidates) == 1:
            return code_candidates[0]
    raise ValueError(
        f"Could not uniquely map club entry {entry.get('ClubName')!r} "
        f"({entry.get('ClubCode')!r}); candidates: {candidates}"
    )


def _team(entry):
    return {
        "skipper": entry.get("SkipperName"),
        "crew": [member.strip() for member in (entry.get("Crew") or "").split(",") if member.strip()],
    }


def _placeholder_team():
    return {"skipper": None, "crew": [None, None, None]}


def _load_season(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _save_season(path, season):
    with path.open("w", encoding="utf-8") as file:
        json.dump(season, file, ensure_ascii=False, indent=4)
        file.write("\n")


def download_entries(overview_url, year, league=None, event=None, data_dir=None):
    """Download selected Manage2Sail entries and update the season file.

    ``event`` is the one-based event number in the overview page.  If omitted,
    all available events are downloaded.  If ``league`` is omitted, both
    leagues are processed.
    """
    base_url = "{uri.scheme}://{uri.netloc}".format(uri=urlsplit(overview_url))
    root = Path(data_dir) if data_dir else Path(__file__).resolve().parents[1] / "data"
    clubs_path = root / "clubs.json"
    clubs = json.loads(clubs_path.read_text(encoding="utf-8"))
    links = _event_links(overview_url, year)
    if event is not None and (event < 1 or event > len(links)):
        raise ValueError(f"event must be between 1 and {len(links)}")

    selected_links = links[event - 1 : event] if event is not None else links
    leagues = (league,) if league is not None else (1, 2)
    updated = []
    for league_number in leagues:
        season_path = root / f"league_{league_number}" / str(year) / "season.json"
        season = _load_season(season_path)
        for event_index, (event_id, title) in enumerate(selected_links, start=1 if event is None else event):
            classes = _event_classes(event_id, base_url)
            league_class = next(
                (
                    item
                    for item in classes
                    if (match := LEAGUE_NAME_PATTERN.match(item["Name"]))
                    and int(match.group(1)) == league_number
                ),
                None,
            )
            if league_class is None:
                continue
            endpoint = (
                f"{base_url}/api/event/{event_id}/regattaentry"
                f"?regattaId={league_class['Id']}"
            )
            entries = json.loads(_get_text(endpoint)).get("Entries", [])
            for entry_data in entries:
                club_id = _club_id(entry_data, clubs)
                club = season.setdefault(club_id, {"events": []})
                while len(club["events"]) < event_index:
                    club["events"].append({"rank": None, "team": _placeholder_team()})
                current_team = club["events"][event_index - 1]["team"]
                if current_team["skipper"] is None:
                    club["events"][event_index - 1]["team"] = _team(entry_data)
            updated.append((league_number, event_index, title, len(entries)))
        _save_season(season_path, season)
    return updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("overview_url", help="Manage2Sail club overview URL")
    parser.add_argument("year", type=int, help="Season year")
    parser.add_argument("--league", type=int, choices=(1, 2), help="Only download this league")
    parser.add_argument("--event", type=int, help="Only download this one-based event number")
    parser.add_argument("--data-dir", type=Path, help="Data directory (defaults to the repository data directory)")
    args = parser.parse_args()

    for league_number, event_number, title, entries in download_entries(
        args.overview_url,
        args.year,
        args.league,
        args.event,
        args.data_dir,
    ):
        print(f"league_{league_number} event_{event_number}: {entries} entries ({title})")


if __name__ == "__main__":
    main()
