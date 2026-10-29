import json
import os

DATA_PATH = "d:\\wm2\\data\\catalog_index.json"
SLANG_PATH = "d:\\wm2\\data\\slang_dictionary.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    catalog = json.load(f)

print("Entidades totales:", len(catalog))
de_to_es = {}
for de, val in catalog.items():
    es = val.get("title_es")
    if es:
        de_to_es[de] = es

print("Total traducciones cargadas DE -> ES:", len(de_to_es))
# Ver si están los materiales de Giftschwert
samples = ["Unbekannter Talisman+", "Dämonenandenken", "Dämonenedelstein", "Yetifell+", "Kriegersymbol", "Weiße Perle", "Blaue Perle", "Blutrote Perle"]
for s in samples:
    print(f"{s} -> {de_to_es.get(s, 'NO TRADUCIDO')}")
