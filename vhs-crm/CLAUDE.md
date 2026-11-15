# VHS-CRM Niederösterreich – Projektkontext für Claude

Interne Web-App (Karte + Dashboard) über alle Mitglieds-Volkshochschulen des Verbands NÖ Volkshochschulen.
Ziel: Veröffentlichung auf **vhs.gr-advice.at** (Hostinger), **nur mit Anmeldung**, nicht in Menüs von gr-advice.at verlinkt.

## Aufbau
| Pfad | Inhalt |
|---|---|
| `src/template.html` | Quelltext der App (Leaflet-Karte, Dashboard, Verzeichnis), Platzhalter für Daten |
| `data/vhs.json` | 68 VHS: Kontakt, Koordinaten, Bezirk, Kurszählung, Kurssuche, Hinweise, Landeskennzahlen (meta.land) |
| `data/kurse.json` | Kurse je VHS nach Fachbereich/Zielgruppe/Format aus der zentralen Kurssuche (Stand 15.11.2026) |
| `data/at_laender.geojson` | Bundesländergrenzen (Kartenbasis, funktioniert ohne Kachelserver) |
| `vendor/leaflet-1.9.4.css` | eingebettetes Leaflet-CSS |
| `build.py` | baut `dist/index.html` (alles eingebettet) + kopiert `deploy/` |
| `import_recherche.py` | übernimmt eine Recherche-CSV (Semikolon) in `data/vhs.json` und prüft Summen |
| `deploy/` | `.htaccess` (HTTPS, noindex, kein Listing) und `robots.txt` |
| `dist/` | fertige Seite zum Hochladen |
| `README.md` | Hostinger-Anleitung Schritt für Schritt |

Bauen: `python3 build.py` → `dist/`. Ansichten: `index.html#karte`, `index.html#dashboard`.

## Datenregeln (verbindlich)
- Nichts erfinden, nichts schätzen, nichts auf Jahreswerte hochrechnen. Leer lassen, wenn nicht belegt.
- **Trägerschaft** (kommunal/Verein) nur mit Beleg je Haus. Derzeit belegt: nur VHS Geras. Landessumme 50/19 laut Leitbild 18.03.2025 (Summe 69 ≠ 68 Einträge).
- „Angebote“ = gezählte Angebote im laufenden Programm 2026/27 (Stand 06.11.2026), **keine Jahreszahlen**; Zeitraum je Haus verschieden.
- Fachbereiche je VHS gibt es nur aus der Kurssuche (46 von 68 VHS) – deckt das tatsächliche Angebot nur teilweise ab.
- Keine Förderangaben aus Gesprächen, keine personenbezogenen Gesprächsnotizen und keine internen Projektinhalte in die App.

## Quellen
- Verbandsverzeichnis: https://www.vhs-noe.at/Verbandsmitglieder/ (Detailseiten `?nr=<id>`; `id` in vhs.json = diese Nummer)
- Zählschnittstelle der Kurssuche: POST `https://www.vhs-noe.at/plugin/vhs/api/course_search_count.php` (Felder vhs, category, category2, veranstaltungsform)
- Landeswerte: VÖV-Statistikbericht 2026, Arbeitsjahr 2024/25
- Geocoding: OpenStreetMap Nominatim (gegen PLZ-Zentren geprüft; Korneuburg nur ortsgenau)

## Offen
1. Veröffentlichung auf Hostinger (Subdomain, SSL, Upload, Passwortschutz) – siehe README.
2. Trägerform je Haus beim Verband anfordern (Mitgliederliste mit Trägerform), dann in `data/vhs.json` nachtragen.
3. Kurssuche-Zahlen regelmäßig aktualisieren (Stichtag sichtbar halten).
4. Mögliche Ausbaustufen: Notizen/Kontakthistorie je VHS (CRM-Funktion), Export als Excel, Kennzahlenblatt je VHS.
