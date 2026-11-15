"""Baut vhs-crm/dist/: index.html (eigenständig, Daten eingebettet) plus Schutzdateien für den Server.

Aufruf:  python3 vhs-crm/build.py
"""
import json
from pathlib import Path

root = Path(__file__).parent
tpl = (root / "src" / "template.html").read_text(encoding="utf-8")
css = (root / "vendor" / "leaflet-1.9.4.css").read_text(encoding="utf-8")
vhs = json.loads((root / "data" / "vhs.json").read_text(encoding="utf-8"))
laender = json.loads((root / "data" / "at_laender.geojson").read_text(encoding="utf-8"))
kpath = root / "data" / "kurse.json"
kurse = json.loads(kpath.read_text(encoding="utf-8")) if kpath.exists() else None

dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = (tpl.replace("/*LEAFLET_CSS*/", css)
           .replace("/*VHS_DATA*/", dump(vhs))
           .replace("/*LAENDER_GEOJSON*/", dump(laender))
           .replace("/*KURSE_DATA*/", dump(kurse)))

# Für den Einsatz außerhalb von claude.ai ein vollständiges HTML-Gerüst ergänzen
page = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n'
        + html + '\n</body>\n</html>\n')
dist = root / "dist"
dist.mkdir(exist_ok=True)
(dist / "index.html").write_text(page, encoding="utf-8")
for f in (root / "deploy").iterdir():
    (dist / f.name).write_bytes(f.read_bytes())
print("dist/ gebaut:", vhs["meta"]["anzahl"], "VHS,", "mit Kurszahlen" if kurse else "ohne Kurszahlen")
