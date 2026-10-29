import re
from .wiki_client import get_image_url

# Diccionario común de traducciones para materiales, stats y términos de la wiki
VOCAB_ES = {
    "Yetifell+": "Piel de Yeti+",
    "Yetifell": "Piel de Yeti",
    "Bärenfußhaut": "Piel de Pata de Oso",
    "Bärenfußhaut+": "Piel de Pata de Oso+",
    "Weißes Haarband+": "Cinta Blanca para el Cabello+",
    "Weißes Haarband": "Cinta Blanca para el Cabello",
    "Zerbrochenes Porzellan": "Porcelana Rota",
    "Kriegersymbol": "Símbolo del Guerrero",
    "Dämonenandenken": "Recuerdo del Demonio",
    "Dämonenandenken+": "Recuerdo del Demonio+",
    "Dämonenedelstein": "Gema del Demonio",
    "Dämonenedelstein+": "Gema del Demonio+",
    "Unbekannter Talisman": "Talismán Desconocido",
    "Unbekannter Talisman+": "Talismán Desconocido+",
    "Weiße Perle": "Perla Blanca",
    "Blaue Perle": "Perla Azul",
    "Blutrote Perle": "Perla Roja",
    "Orkzahn": "Diente de Orco",
    "Orkzahn+": "Diente de Orco+",
    "Ork-Wurrzahn": "Diente de Orco con Raíz",
    "Schlangenhaut": "Piel de Serpiente",
    "Spinnensack": "Bolsa de Huevos de Araña",
    "Spinnen-Augen": "Ojos de Araña",
    "Spinnenbeine": "Patas de Araña",
    "Skorpionschwanz": "Cola de Escorpión",
    "Skorpionschwanz+": "Cola de Escorpión+",
    "Skorpionnadel": "Aguijón de Escorpión",
    "Fischgräte": "Espina de Pescado",
    "Muschel": "Almeja",
    "Stück Edelstein": "Trozo de Gema",
    "Stück kaputter Rüstung": "Trozo de Armadura Rota",
    "Rostige Klinge": "Espada Oxidada",
    "Shiriken": "Shuriken",
    "Shiriken+": "Shuriken+",
    "Eisstück": "Trozo de Hielo",
    "Eisstück+": "Trozo de Hielo+",
    "Eiskugel": "Bola de Hielo",
    "Eiskugel+": "Bola de Hielo+",
    "Flammenmähne": "Melena Llameante",
    "Krieger": "Guerrero",
    "Sura": "Sura",
    "Ninja": "Ninja",
    "Schamane": "Chamán",
    "Lykaner": "Licano",
    "Einhänder": "Espada de 1 Mano",
    "Zweihänder": "Espada de 2 Manos",
    "Dolch": "Dagas",
    "Bogen": "Arco",
    "Glocke": "Campana",
    "Fächer": "Abanico",
    "Klauen": "Garras",
    "Truhen": "Cofres",
    "Monster": "Monstruos",
    "Sonstiges": "Otros",
    "Waffenhändler": "Vendedor de Armas",
    "Rüstungshändler": "Vendedor de Armaduras",
    "Metins": "Metins",
    "Metinsteine": "Metins",
    "Angriffswert": "Valor de Ataque",
    "Magischer Angriffswert": "Ataque Mágico",
    "Verteidigung": "Defensa"
}

def translate_term(term):
    if not term:
        return ""
    t_clean = term.strip()
    return VOCAB_ES.get(t_clean, t_clean)

def clean_wiki_markup(text):
    if not text:
        return ""
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'{2,5}", "", text)
    # Traducir palabras clave comunes en texto libre
    for de_w, es_w in VOCAB_ES.items():
        text = re.sub(rf"\b{re.escape(de_w)}\b", es_w, text)
    return re.sub(r"\s+", " ", text).strip()

def parse_icons_with_urls(raw_text):
    """
    Detecta {{icon|Nombre}} o {{icon2|Nombre|Texto}} o 1x {{icon|...}}
    y asocia la URL del icono oficial y la traducción en español.
    """
    items = []
    
    # 1. {{icon|Item}}
    pattern1 = re.findall(r"(?:(\d+)x\s*)?\{\{icon\|([^}]+)\}\}", raw_text)
    for cant, item_name in pattern1:
        cant_str = f"{cant}x " if cant else ""
        item_clean = item_name.strip()
        img_url = get_image_url(item_clean)
        es_name = translate_term(item_clean)
        items.append({
            "name": item_clean,
            "name_es": es_name,
            "display": f"{cant_str}{es_name}",
            "icon_url": img_url
        })
        
    # 2. {{icon2|Item|Etiqueta}}
    pattern2 = re.findall(r"(?:(\d+)x\s*)?\{\{icon2\|([^}|]+)(?:\|([^}]+))?\}\}", raw_text)
    for cant, item_name, label in pattern2:
        item_clean = item_name.strip()
        disp_name = label.strip() if label else item_clean
        cant_str = f"{cant}x " if cant else ""
        img_url = get_image_url(item_clean)
        es_name = translate_term(disp_name)
        items.append({
            "name": item_clean,
            "name_es": es_name,
            "display": f"{cant_str}{es_name}",
            "icon_url": img_url
        })
        
    return items

def parse_equipment_layout(wikitext, target_plus=None):
    data = {}
    
    # Datos básicos
    level_match = re.search(r"\|Level\s*=\s*([^|\n\r]+)", wikitext)
    classes_match = re.search(r"\|Klassen\s*=\s*([^|\n\r]+)", wikitext)
    type_match = re.search(r"\|(?:Waffenart|Rüstungstyp)\s*=\s*([^|\n\r]+)", wikitext)
    image_match = re.search(r"\|IG-Bild\s*=\s*([^|\n\r]+)", wikitext)
    
    data["level"] = clean_wiki_markup(level_match.group(1)) if level_match else None
    data["classes"] = clean_wiki_markup(classes_match.group(1)) if classes_match else None
    data["type"] = clean_wiki_markup(type_match.group(1)) if type_match else None
    
    if image_match:
        img_file = image_match.group(1).strip()
        data["main_image"] = get_image_url(img_file)
    else:
        data["main_image"] = None
    
    # Costes
    kosten = dict(re.findall(r"\|Kosten(\d+)\s*=\s*([^|\n\r]+)", wikitext))
    
    # Extraer todas las líneas |Upgradeitem-X-Y = valor completo
    upgrade_items_map = {}
    for line in wikitext.split("\n"):
        match_up = re.match(r"^\|Upgradeitem-\d+-(\d+)\s*=\s*(.+)$", line.strip())
        if match_up:
            lvl_num = int(match_up.group(1))
            val_text = match_up.group(2)
            if lvl_num not in upgrade_items_map:
                upgrade_items_map[lvl_num] = []
            upgrade_items_map[lvl_num].append(val_text)

    upgrades = []
    for i in range(1, 10):
        lvl_key = str(i)
        
        # Filtrar si el usuario pidió un nivel específico (ej: +9)
        if target_plus is not None and target_plus != i:
            continue
            
        cost = kosten.get(lvl_key, "0").strip()
        
        # Parsear materiales de este nivel
        raw_mats_lines = upgrade_items_map.get(i, [])
        materials_parsed = []
        for mr in raw_mats_lines:
            materials_parsed.extend(parse_icons_with_urls(mr))
            
        # Valores de Ataque / Defensa
        aw = re.search(rf"\|AW{i}\s*=\s*([^|\n\r]+)", wikitext)
        maw = re.search(rf"\|MAW{i}\s*=\s*([^|\n\r]+)", wikitext)
        def_val = re.search(rf"\|Verteidigung{i}\s*=\s*([^|\n\r]+)", wikitext)
        
        stats = []
        if aw:
            stats.append(f"Ataque: {aw.group(1).strip()}")
        if maw:
            stats.append(f"Ataque Mágico: {maw.group(1).strip()}")
        if def_val:
            stats.append(f"Defensa: {def_val.group(1).strip()}")
            
        upgrades.append({
            "from_to": f"+{i-1} -> +{i}",
            "yang": f"{cost} Yang",
            "materials": materials_parsed,
            "stats": stats
        })
        
    data["upgrades"] = upgrades
    
    # Origen / Drops
    herkunft_match = re.search(r"\|Herkunft\s*=\s*(.*?)(?=\n\|[A-Za-z0-9_-]+\s*=|(?:\}\}))", wikitext, re.DOTALL)
    if herkunft_match:
        data["drops_raw"] = clean_wiki_markup(herkunft_match.group(1))
    else:
        data["drops_raw"] = None
        
    return data

def parse_quest_layout(wikitext):
    level = re.search(r"\|Level\s*=\s*([^|\n\r]+)", wikitext)
    questgeber = re.search(r"\|Questgeber\s*=\s*([^|\n\r]+)", wikitext)
    items_raw = re.search(r"\|Items\s*=\s*(.*?)(?=\n\|[A-Za-z0-9_-]+\s*=)", wikitext, re.DOTALL)
    belohnung_raw = re.search(r"\|Belohnung\s*=\s*(.*?)(?=\n\|[A-Za-z0-9_-]+\s*=)", wikitext, re.DOTALL)
    loesung_raw = re.search(r"\|Lösung\s*=\s*(.*?)(?=\n\|[A-Za-z0-9_-]+\s*=)", wikitext, re.DOTALL)
    
    items_list = parse_icons_with_urls(items_raw.group(1)) if items_raw else []
    rewards_list = parse_icons_with_urls(belohnung_raw.group(1)) if belohnung_raw else []
    
    return {
        "level": clean_wiki_markup(level.group(1)) if level else "Cualquiera",
        "quest_giver": clean_wiki_markup(questgeber.group(1)) if questgeber else "Desconocido",
        "items": items_list,
        "rewards": rewards_list,
        "rewards_text": clean_wiki_markup(belohnung_raw.group(1)) if belohnung_raw else "",
        "solution": clean_wiki_markup(loesung_raw.group(1)) if loesung_raw else ""
    }

def parse_monster_layout(wikitext):
    level = re.search(r"\|Level\s*=\s*([^|\n\r]+)", wikitext)
    rang = re.search(r"\|Rang\s*=\s*([^|\n\r]+)", wikitext)
    element = re.search(r"\|Element\s*=\s*([^|\n\r]+)", wikitext)
    drops_raw = re.search(r"\|Drops\s*=\s*(.*?)(?=\n\|[A-Za-z0-9_-]+\s*=)", wikitext, re.DOTALL)
    
    drops_list = parse_icons_with_urls(drops_raw.group(1)) if drops_raw else []
    
    return {
        "level": clean_wiki_markup(level.group(1)) if level else "N/A",
        "rank": clean_wiki_markup(rang.group(1)) if rang else "N/A",
        "element": clean_wiki_markup(element.group(1)) if element else "Ninguno",
        "drops": drops_list,
        "drops_text": clean_wiki_markup(drops_raw.group(1)) if drops_raw else ""
    }
