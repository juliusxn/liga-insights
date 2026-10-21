"""Create season data files from a JSON season configuration."""

import argparse
import json
from pathlib import Path


def _placeholder_event():
    return {
        "rank": None,
        "team": {
            "skipper": None,
            "crew": [None, None, None],
        },
    }


def _load_clubs(data_dir):
    clubs_path = data_dir / "clubs.json"
    with clubs_path.open(encoding="utf-8") as file:
        return clubs_path, json.load(file)


def _event_count_from_manifest(data_dir, year, league):
    manifest = _load_manifest(data_dir)
    seasons = manifest["competition"][f"league_{league}"]["seasons"]
    for season in seasons:
        if season["year"] == year:
            return season["events"]
    raise ValueError(
        f"no event count found in manifest.json for league {league}, year {year}"
    )


def _load_manifest(data_dir):
    manifest_path = data_dir / "manifest.json"
    with manifest_path.open(encoding="utf-8") as file:
        return json.load(file)


def create_season(
    year, league, event_count, club_ids, data_dir=None, overwrite=False
):
    """Create and return a new season file for the supplied club IDs.

    The season rank is initialized to ``None`` because it cannot be inferred
    from the club list. Event ranks and team data are initialized as
    placeholders for later downloads.
    """
    if year < 1:
        raise ValueError("year must be a positive integer")
    if league not in (1, 2):
        raise ValueError("league must be 1 or 2")
    if event_count < 1:
        raise ValueError("event_count must be a positive integer")

    club_ids = list(club_ids)
    if len(set(club_ids)) != len(club_ids):
        duplicates = sorted({club_id for club_id in club_ids if club_ids.count(club_id) > 1})
        raise ValueError(f"duplicate club IDs: {duplicates}")

    root = (
        Path(data_dir)
        if data_dir is not None
        else Path(__file__).resolve().parents[1] / "data"
    )
    clubs_path, clubs = _load_clubs(root)

    missing = sorted(set(club_ids) - set(clubs))
    if missing:
        raise ValueError(f"club IDs not found in {clubs_path}: {missing}")

    season_path = root / f"league_{league}" / str(year) / "season.json"
    if season_path.exists() and not overwrite:
        raise FileExistsError(
            f"{season_path} already exists; pass overwrite=True or use --force to replace it"
        )
    season_path.parent.mkdir(parents=True, exist_ok=True)

    season = {
        club_id: {
            "events": [_placeholder_event() for _ in range(event_count)],
            "season": None,
        }
        for club_id in club_ids
    }
    with season_path.open("w", encoding="utf-8") as file:
        json.dump(season, file, ensure_ascii=False, indent=4)
        file.write("\n")
    return season_path


def create_seasons_from_file(
    config_path, data_dir=None, event_count=None, overwrite=False
):
    """Create season files from a configuration JSON file.

    The configuration must contain a positive ``year``, a positive ``events``
    count, and one or more league keys, for example
    ``{"year": 2027, "events": 6, "league_1": ["BA001", "B046"]}``.
    League keys must match the keys under ``competition`` in ``manifest.json``
    (for example, ``"league_1"``). If ``event_count`` is omitted, the
    ``events`` value is used. For backwards compatibility, the manifest is
    used only when ``events`` is omitted.
    """
    config_path = Path(config_path)
    with config_path.open(encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict) or "year" not in config:
        raise ValueError("configuration must be an object containing a 'year'")
    year = config["year"]
    if not isinstance(year, int) or isinstance(year, bool) or year < 1:
        raise ValueError("configuration 'year' must be a positive integer")
    configured_events = config.get("events")
    if configured_events is not None and (
        not isinstance(configured_events, int)
        or isinstance(configured_events, bool)
        or configured_events < 1
    ):
        raise ValueError("configuration 'events' must be a positive integer")

    leagues = {}
    for key, club_ids in config.items():
        if key in ("year", "events"):
            continue
        league_key = str(key)
        if not isinstance(club_ids, list) or not club_ids:
            raise ValueError(f"league {league_key} must contain a non-empty list of club IDs")
        if league_key in leagues:
            raise ValueError(f"league {league_key} is specified more than once")
        leagues[league_key] = club_ids
    if not leagues:
        raise ValueError("configuration must contain at least one league")

    root = (
        Path(data_dir)
        if data_dir is not None
        else Path(__file__).resolve().parents[1] / "data"
    )
    manifest = _load_manifest(root)
    manifest_leagues = manifest.get("competition", {})
    invalid_keys = sorted(
        key
        for key in config
        if key not in {"year", "events"} and key not in manifest_leagues
    )
    if invalid_keys:
        raise ValueError(
            "configuration contains league keys not present in manifest.json: "
            f"{invalid_keys}; expected one of {sorted(manifest_leagues)}"
        )

    paths = []
    for league_key, club_ids in leagues.items():
        league = int(league_key.removeprefix("league_"))
        count = (
            event_count
            if event_count is not None
            else (
                configured_events
                if configured_events is not None
                else _event_count_from_manifest(root, year, league)
            )
        )
        paths.append(
            create_season(
                year,
                league,
                count,
                club_ids,
                data_dir=root,
                overwrite=overwrite,
            )
        )
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="JSON file containing year and league club IDs")
    parser.add_argument(
        "--events",
        type=int,
        help="Number of events; defaults to the value in data/manifest.json",
    )
    parser.add_argument("--data-dir", type=Path, help="Data directory")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing season file")
    args = parser.parse_args()

    paths = create_seasons_from_file(
        args.config,
        data_dir=args.data_dir,
        event_count=args.events,
        overwrite=args.force,
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
