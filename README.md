# liga-insights
This repository provides result insights for the [Deutsche Segelbundesliga](https://segelbundesliga.de).

## Beispiele
Beispiele sind in `src/display.ipynb`

### Ewige Bestenliste
Regeln:
- `2. Liga` wird "angehängt". Sieger `2. Liga` bekommt `19` Punkte, usw. bis `36` Punkte
- Keine Teilnahme gibt `36+1` Punkte. Aussnahme 2014: `18+1` Punkte, da keine `2. Liga`

### Entries herunterladen

Einträge von Manage2Sail können mit `src/download.py` in die jeweilige
`season.json` geschrieben werden:

```bash
python -m src.download \
  "https://www.manage2sail.com/en-US/Club/Detail/<club-id>" \
  2026 \
  --league 1 \
  --event 3
```

`--league` und `--event` sind optional. Ohne diese Optionen werden beide
Ligen und alle verfügbaren Events geladen. Die vorhandene Saison-Datei muss
existieren; eine leere JSON-Datei (`{}`) wird mit den gefundenen Clubs und
Teams befüllt.

Neue Saison-Dateien können mit einer JSON-Konfiguration angelegt werden:

```bash
python -m src.data_utils season-config.json
```

Die Konfiguration enthält das Jahr sowie eine Liste von Club-IDs pro Liga:

```json
{
    "year": 2027,
    "events": 6,
    "league_1": ["HA002", "B004", "BA003"],
    "league_2": ["BA001", "B046"]
}
```

Die Schlüssel `league_1` und `league_2` müssen exakt den Schlüsseln unter
`competition` in `data/manifest.json` entsprechen. Die Club-IDs werden gegen
`data/clubs.json` geprüft. Die Anzahl der Events wird
aus dem `events`-Eintrag gelesen und kann mit `--events 6` überschrieben werden.
Falls `events` fehlt, wird die Anzahl weiterhin aus `data/manifest.json`
gelesen. Die Dateien werden mit Platzhalter-Events angelegt. Vorhandene
Dateien werden nur mit `--force` überschrieben.
