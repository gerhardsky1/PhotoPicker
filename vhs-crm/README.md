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

## Veröffentlichen auf vhs.gr-advice.at (Hostinger, nur mit Anmeldung)
1. **Subdomain anlegen:** hPanel → Domains → Subdomains → Name `vhs`, Domain `gr-advice.at`, Ordner übernehmen (z. B. `public_html/vhs`).
2. **SSL:** hPanel → Sicherheit → SSL → für `vhs.gr-advice.at` installieren (meist automatisch, kann bis zu ein paar Stunden dauern).
3. **Hochladen:** hPanel → Dateien → Dateimanager → in den Subdomain-Ordner wechseln → `vhs-crm-upload.zip` hochladen → Rechtsklick → Entpacken. Danach müssen dort `index.html`, `robots.txt` und `.htaccess` liegen (versteckte Dateien ggf. einblenden). Die ZIP-Datei danach löschen.
4. **Passwortschutz:** hPanel → Erweitert → Passwortgeschützte Verzeichnisse → Subdomain-Ordner wählen → Benutzername und starkes Passwort setzen. Erst **nach** dem Hochladen machen, damit die `.htaccess` nicht überschrieben wird.
5. **Prüfen:** `https://vhs.gr-advice.at` im privaten Fenster öffnen → Anmeldefenster muss erscheinen; ohne Passwort darf nichts zu sehen sein. Die Subdomain nirgends auf gr-advice.at verlinken.

Aktualisieren: `python3 build.py`, dann nur `dist/index.html` im Dateimanager ersetzen.

Schutz: HTTP-Basic-Auth über HTTPS, `noindex` (Meta-Tag und Header), `robots.txt` sperrt alles, kein Verzeichnis-Listing.
