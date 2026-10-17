import json

from config.paths import CLUBS_FILE, DATA_DIR, MANIFEST_FILE
from test_utils import _unique_object_pairs


def test_all_result_clubs_are_in_registry():
    with CLUBS_FILE.open(encoding="utf-8") as file:
        clubs = json.load(file)

    with MANIFEST_FILE.open(encoding="utf-8") as file:
        manifest = json.load(file)

    result_clubs = set()
    for competition in manifest["competition"].values():
        for season in competition["seasons"]:
            result_file = DATA_DIR / season["ranking_file"]
            with result_file.open(encoding="utf-8") as file:
                result_clubs.update(json.load(file))

    missing_clubs = result_clubs - clubs.keys()
    assert not missing_clubs, f"Result files contain club IDs missing from the registry: " f"{sorted(missing_clubs)}"


def test_result_files_have_unique_clubs_per_year():
    with MANIFEST_FILE.open(encoding="utf-8") as file:
        manifest = json.load(file)

    clubs_by_league_and_year = {}
    for league, competition in manifest["competition"].items():
        for season in competition["seasons"]:
            result_file = DATA_DIR / season["ranking_file"]
            with result_file.open(encoding="utf-8") as file:
                clubs = json.load(file, object_pairs_hook=_unique_object_pairs)
            clubs_by_league_and_year[league, season["year"]] = set(clubs)

    for year in {
        year
        for league, year in clubs_by_league_and_year
        if ("league_1", year) in clubs_by_league_and_year and ("league_2", year) in clubs_by_league_and_year
    }:
        overlapping_clubs = clubs_by_league_and_year["league_1", year] & clubs_by_league_and_year["league_2", year]
        assert not overlapping_clubs, f"Club IDs occur in both leagues in {year}: " f"{sorted(overlapping_clubs)}"


def test_result_files_have_unique_places_per_event():
    with MANIFEST_FILE.open(encoding="utf-8") as file:
        manifest = json.load(file)

    for league, competition in manifest["competition"].items():
        for season in competition["seasons"]:
            result_file = DATA_DIR / season["ranking_file"]
            with result_file.open(encoding="utf-8") as file:
                results = json.load(file)

            event_places = list(zip(*(club["events"] for club in results.values())))
            for event_number, places in enumerate(event_places, start=1):
                duplicate_places = {place for place in places if places.count(place) > 1}
                assert not duplicate_places, (
                    f"Duplicate places in {league} {season['year']} "
                    f"event {event_number}: {sorted(duplicate_places)}"
                )
