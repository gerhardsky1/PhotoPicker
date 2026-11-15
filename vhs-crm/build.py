"""Baut vhs-crm/index.html: eine eigenständige Datei mit eingebetteten Daten.

Aufruf:  python3 vhs-crm/build.py
"""
import json
from pathlib import Path

root = Path(__file__).parent
tpl = (root / "src" / "template.html").read_text(encoding="utf-8")
css = (root / "vendor" / "leaflet-1.9.4.css").read_text(encoding="utf-8")
vhs = json.loads((root / "data" / "vhs.json").read_text(encoding="utf-8"))
laender = json.loads((root / "data" / "at_laender.geojson").read_text(encoding="utf-8"))

dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = (tpl.replace("/*LEAFLET_CSS*/", css)
           .replace("/*VHS_DATA*/", dump(vhs))
           .replace("/*LAENDER_GEOJSON*/", dump(laender)))

# Für den Einsatz außerhalb von claude.ai ein vollständiges HTML-Gerüst ergänzen
page = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
        + html + '\n</body>\n</html>\n')
(root / "index.html").write_text(page, encoding="utf-8")
(root / "artifact.html").write_text(html, encoding="utf-8")
print("index.html und artifact.html gebaut:", vhs["meta"]["anzahl"], "VHS")
