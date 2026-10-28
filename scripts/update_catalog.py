import urllib.request
import urllib.parse
import json
import time
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

API_URL = "https://de-wiki.metin2.gameforge.com/api.php"
HEADERS = {"User-Agent": "Metin2CatalogBuilder/1.0 (contact@example.com)"}
OUTPUT_FILE = "d:\\wm2\\catalog_index.json"

CATEGORIES = [
    {"name": "Waffen", "type": "weapon"},
    {"name": "Rüstungen", "type": "armor"},
    {"name": "Helme", "type": "helmet"},
    {"name": "Schilde", "type": "shield"},
    {"name": "Ohrringe", "type": "earring"},
    {"name": "Armbänder", "type": "bracelet"},
    {"name": "Halsketten", "type": "necklace"},
    {"name": "Schuhe", "type": "shoes"},
    {"name": "Gürtel", "type": "belt"},
    {"name": "Talismane", "type": "talisman"},
    {"name": "Items/Aufwertung", "type": "upgrade_material"},
    {"name": "Items/Container", "type": "chest"},
    {"name": "Items/Bücher", "type": "book"},
    {"name": "Gegner/Bosse", "type": "boss"},
    {"name": "Gegner/Metins", "type": "metin"},
    {"name": "Gegner", "type": "monster"},
    {"name": "Quests", "type": "quest"},
    {"name": "NPC", "type": "npc"},
]

def fetch_api(params):
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error en petición ({params.get('cmtitle') or params.get('titles')}): {e}")
        return None

def get_category_pages(cat_name):
    pages = []
    cmcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Kategorie:{cat_name}",
            "cmnamespace": "0", # Solo artículos de contenido principal
            "cmlimit": "500",
            "format": "json"
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
            
        data = fetch_api(params)
        if not data:
            break
            
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            pages.append(m["title"])
            
        if "continue" in data and "cmcontinue" in data["continue"]:
            cmcontinue = data["continue"]["cmcontinue"]
        else:
            break
            
    return pages

def get_spanish_translations(titles_batch):
    """
    Obtiene traducciones en español para un lote de hasta 50 títulos a la vez
    usando prop=langlinks con lllang=es
    """
    params = {
        "action": "query",
        "prop": "langlinks",
        "titles": "|".join(titles_batch),
        "lllang": "es",
        "format": "json"
    }
    data = fetch_api(params)
    translations = {}
    if data:
        pages = data.get("query", {}).get("pages", {})
        for _, p in pages.items():
            t_de = p.get("title")
            ll = p.get("langlinks", [])
            if ll:
                translations[t_de] = ll[0].get("*")
    return translations

def build_catalog():
    print("=" * 60)
    print("CONSTRUCCIÓN DEL CATÁLOGO MAESTRO (DE -> ES)")
    print("=" * 60)
    
    catalog = {}
    
    # 1. Recorrer categorías clave
    for cat in CATEGORIES:
        c_name = cat["name"]
        c_type = cat["type"]
        print(f"Indexando categoría: Kategorie:{c_name}...")
        pages = get_category_pages(c_name)
        print(f" -> {len(pages)} páginas encontradas.")
        
        for p in pages:
            if p not in catalog:
                catalog[p] = {
                    "title_de": p,
                    "title_es": None,
                    "type": c_type,
                    "categories": [c_name]
                }
            else:
                if c_name not in catalog[p]["categories"]:
                    catalog[p]["categories"].append(c_name)
        time.sleep(0.3)

    print(f"\nTotal entidades únicas indexadas: {len(catalog)}")
    print("\nObteniendo nombres equivalentes en español en bloques de 50...")

    all_titles = list(catalog.keys())
    batch_size = 50
    for i in range(0, len(all_titles), batch_size):
        batch = all_titles[i:i+batch_size]
        trans = get_spanish_translations(batch)
        for t_de, t_es in trans.items():
            if t_de in catalog:
                catalog[t_de]["title_es"] = t_es
        print(f"Progreso traducciones: {min(i + batch_size, len(all_titles))}/{len(all_titles)}", end="\r")
        time.sleep(0.2)

    print(f"\nGuardando catálogo en {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    # Estadísticas finales
    con_es = sum(1 for item in catalog.values() if item.get("title_es"))
    print("\n" + "=" * 60)
    print("CATÁLOGO COMPLETADO CON ÉXITO")
    print(f"Entidades totales: {len(catalog)}")
    print(f"Entidades con traducción directa en español: {con_es}")
    print("=" * 60)

if __name__ == "__main__":
    build_catalog()
