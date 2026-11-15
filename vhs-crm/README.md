# VHS-CRM Niederösterreich

Interne Web-App für den Verband NÖ Volkshochschulen: Karte und Dashboard aller Mitglieds-VHS.

- **Karte** (`#karte`): alle VHS mit Suche, Liste und Kontaktdetails
- **Dashboard** (`#dashboard`): Kennzahlen, Kurse nach Fachbereich, Zielgruppen und Formate, Verzeichnis mit Trägerschaft, Ansprechperson, Kontakt, Kursanzahl und inhaltlichem Angebot

## Daten
| Datei | Inhalt | Quelle |
|---|---|---|
| `data/vhs.json` | 68 Mitglieds-VHS, Kontakt, Koordinaten, Trägerschafts-Indiz | vhs-noe.at/Verbandsmitglieder, Geocoding OpenStreetMap Nominatim |
| `data/kurse.json` | Kurszahlen je VHS (optional) | zentrale Kurssuche vhs-noe.at |
| `data/at_laender.geojson` | Bundesländergrenzen | @highcharts/map-collection |

**Trägerschaft (kommunal/Verein) ist nur ein Indiz** aus den Kontaktadressen (Gemeinde-Domain vs. eigene VHS-Domain) und muss vom Verband bestätigt werden.

## Bauen
```
python3 build.py      # erzeugt dist/index.html (+ .htaccess, robots.txt)
```

## Veröffentlichen auf vhs.gr-advice.at (nur mit Anmeldung)
1. Subdomain `vhs.gr-advice.at` beim Hoster anlegen, eigenes Verzeichnis, SSL-Zertifikat aktivieren.
2. Inhalt von `dist/` hochladen (inkl. der versteckten Datei `.htaccess`).
3. Passwortdatei **außerhalb** des Web-Verzeichnisses anlegen, z. B. per SSH: `htpasswd -c /pfad/.htpasswd benutzername` – oder über den Verzeichnisschutz im Hoster-Panel.
4. In `.htaccess` die Zeile `AuthUserFile` auf diesen absoluten Pfad setzen.
5. Prüfen: Aufruf ohne Passwort muss 401 liefern; die Subdomain nirgends auf gr-advice.at verlinken.

Schutz: HTTP-Basic-Auth über HTTPS, `noindex` (Meta-Tag und Header), `robots.txt` sperrt alles, kein Verzeichnis-Listing.
