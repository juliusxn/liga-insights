def _unique_object_pairs(pairs):
    clubs = {}
    for key, value in pairs:
        if key in clubs:
            raise AssertionError(f"Duplicate club ID: {key}")
        clubs[key] = value
    return clubs
