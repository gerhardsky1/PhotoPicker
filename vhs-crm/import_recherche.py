"""Übernimmt die Recherche-CSV (eigene Recherche) in data/vhs.json.

Aufruf:  python3 import_recherche.py <pfad/zur/vhs_daten.csv>

Bewusst NICHT übernommen: Spalte budget_oder_foerderung (nur Gesprächsangaben, nicht belegt).
Trägerschaft wird nur übernommen, wo ein Beleg vorliegt; sonst „unbelegt“.
"""
import csv, json, re, sys
from pathlib import Path

root = Path(__file__).parent
src = Path(sys.argv[1])
rows = [r for r in csv.DictReader(src.open(encoding="utf-8"), delimiter=";") if r["name"]]
data = json.loads((root / "data" / "vhs.json").read_text(encoding="utf-8"))
by_id = {v["id"]: v for v in data["vhs"]}

def parse_besonderheiten(text):
    out = {"bezirk": "", "amt": "", "spanne": "", "zaehlquelle": "", "sicherheit": "",
           "portal": None, "im_portal": None, "keine_zahl": "", "jahreszahl": "", "zahlenquelle": "", "hinweise": []}
    for part in [p.strip() for p in text.split(" · ") if p.strip()]:
        if part.startswith("Bezirk: "): out["bezirk"] = part[8:]
        elif part.startswith("Adresse: "): pass  # Adresse kommt aus dem Verbandsverzeichnis
        elif part.startswith("Leitung mit kommunalpolitischem Amt: "): out["amt"] = part.split(": ", 1)[1].rstrip(".")
        elif part.startswith("Kurszählung: "):
            m = re.match(r"Kurszählung: Spanne (.+?), Quelle (.+), Sicherheit (\w+)", part)
            if m: out["spanne"], out["zaehlquelle"], out["sicherheit"] = m.groups()
            else: out["hinweise"].append(part)
        elif part.startswith("davon in der Verbands-Kurssuche sichtbar: "):
            out["portal"] = int(re.match(r"davon in der Verbands-Kurssuche sichtbar: (\d+)", part).group(1)); out["im_portal"] = True
            rest = part.split(re.match(r"davon in der Verbands-Kurssuche sichtbar: \d+", part).group(0), 1)[1].strip(" ;·")
            if rest: out["hinweise"].append(rest)
        elif "nicht in der Kurssuche" in part:
            out["im_portal"] = False
            rest = part.replace("nicht in der Kurssuche", "").strip(" ;·")
            if rest: out["hinweise"].append(rest)
        elif part.startswith("Keine Kurszahl ermittelbar: "): out["keine_zahl"] = part.split(": ", 1)[1]
        elif part.startswith("Publizierte Jahreszahl Kurse: "): out["jahreszahl"] = part.split(": ", 1)[1]
        elif part.startswith("Zahlenquelle: "): out["zahlenquelle"] = part.split(": ", 1)[1]
        else: out["hinweise"].append(part)
    if "nicht in der Kurssuche" in text: out["im_portal"] = False
    return out

for r in rows:
    nr = re.search(r"nr=(\d+)", r["quelle_url"]).group(1)
    v = by_id[nr]
    b = parse_besonderheiten(r["besonderheiten"])
    v["bezirk"] = b["bezirk"]
    v["kommunalpolitisches_amt"] = b["amt"]
    v["ansprechperson"] = r["ansprechperson"]
    if not r["website"]: v["web"] = ""   # Schrems: Verzeichnis nennt nur die Verbandsseite
    v["kurse"] = {
        "anzahl": int(r["kurse_anzahl"]) if r["kurse_anzahl"] else None,
        "untergrenze": b["spanne"].startswith("≥"),
        "spanne": b["spanne"], "zeitraum": r["kurse_zeitraum"], "zaehlquelle": b["zaehlquelle"],
        "sicherheit": b["sicherheit"], "vertrauen": r["vertrauen"],
        "im_portal": b["im_portal"] if b["im_portal"] is not None else None,
        "portal_sichtbar": b["portal"], "keine_zahl_grund": b["keine_zahl"],
        "stand": "2026-11-06",
    }
    v["jahreswerte"] = {"teilnehmende": r["teilnehmende"], "kurse_jahr": b["jahreszahl"], "quelle": b["zahlenquelle"]}
    v["hinweise"] = b["hinweise"]
    if r["traeger"] in ("kommunal", "verein") and r["traeger_beleg"]:
        v["traeger"] = {"wert": r["traeger"], "quelle": "beleg", "grund": r["traeger_beleg"]}
    else:
        v["traeger"] = {"wert": "unbelegt", "quelle": "", "grund": "Trägerform je Haus nicht veröffentlicht"}

data["meta"]["recherche"] = {"quelle": "Eigene Recherche, Stand 15.11.2026",
                             "kurszaehlung": "2026-11-06", "verzeichnis": "2026-10-30"}
data["meta"].pop("traeger_hinweis", None)
(root / "data" / "vhs.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

# Plausibilisierung gegen die Übergabedokumentation
V = data["vhs"]
mit = [v for v in V if v["kurse"]["anzahl"] is not None]
print("VHS:", len(V), "| mit Kurszahl:", len(mit), "(erwartet 56) | Summe:", sum(v["kurse"]["anzahl"] for v in mit), "(erwartet 3.474)")
print("kommunalpolitisches Amt:", sum(1 for v in V if v["kommunalpolitisches_amt"]), "(erwartet 17)")
print("im Portal:", sum(1 for v in V if v["kurse"]["im_portal"]), "| nicht:", sum(1 for v in V if v["kurse"]["im_portal"] is False),
      "| offen:", [v["name"] for v in V if v["kurse"]["im_portal"] is None])
both = [v for v in mit if v["kurse"]["im_portal"] and v["kurse"]["zaehlquelle"] and "nur Verbands-Kurssuche" not in v["kurse"]["zaehlquelle"]]
print("eigenes Programm + Portal:", len(both), "Häuser,", sum(v["kurse"]["portal_sichtbar"] for v in both), "von", sum(v["kurse"]["anzahl"] for v in both), "(erwartet 22 / 1.395 von 2.060)")
kl = {"150+": 0, "100–149": 0, "50–99": 0, "20–49": 0, "1–19": 0, "keine": 0}
for v in V:
    n = v["kurse"]["anzahl"]
    kl["keine" if n is None else "150+" if n >= 150 else "100–149" if n >= 100 else "50–99" if n >= 50 else "20–49" if n >= 20 else "1–19"] += 1
print("Größenklassen:", kl, "(erwartet 6/8/6/19/17/12)")
print("Vertrauen:", {k: sum(1 for v in V if v["kurse"]["vertrauen"] == k) for k in ("hoch", "mittel", "niedrig")}, "(erwartet 23/25/20)")
print("Bezirke:", len({v["bezirk"] for v in V}), "| Träger belegt:", [v["name"] for v in V if v["traeger"]["quelle"] == "beleg"])
