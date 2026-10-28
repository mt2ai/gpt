import re
from .wiki_client import get_image_url

def clean_wiki_markup(text):
    """Limpia enlaces y marcas básicas de wikitext"""
    if not text:
        return ""
    # [[Enlace|Texto]] -> Texto, [[Enlace]] -> Enlace
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    # Quitar negritas y cursivas
    text = re.sub(r"'{2,5}", "", text)
    # Quitar saltos excesivos
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_icons_with_urls(raw_text):
    """
    Detecta {{icon|Nombre}} o {{icon2|Nombre|Texto}} o 1x {{icon|...}}
    y asocia la URL del icono oficial
    """
    items = []
    # Buscar patrones como "2x {{icon|Bärenfußhaut}}" o "{{icon2|Orkzahn|10x}}"
    # 1. {{icon|Item}}
    pattern1 = re.findall(r"(?:(\d+)x\s*)?\{\{icon\|([^}]+)\}\}", raw_text)
    for cant, item_name in pattern1:
        cant_str = f"{cant}x " if cant else ""
        img_url = get_image_url(item_name)
        items.append({
            "name": item_name,
            "display": f"{cant_str}{item_name}",
            "icon_url": img_url
        })
        
    # 2. {{icon2|Item|Etiqueta}}
    pattern2 = re.findall(r"(?:(\d+)x\s*)?\{\{icon2\|([^}|]+)(?:\|([^}]+))?\}\}", raw_text)
    for cant, item_name, label in pattern2:
        disp_name = label if label else item_name
        cant_str = f"{cant}x " if cant else ""
        img_url = get_image_url(item_name)
        items.append({
            "name": item_name,
            "display": f"{cant_str}{disp_name}",
            "icon_url": img_url
        })
        
    return items

def parse_equipment_layout(wikitext, target_plus=None):
    """
    Parsea plantillas Waffe/Layout y Rüstung/Layout
    """
    data = {}
    
    # Datos básicos
    level_match = re.search(r"\|Level\s*=\s*([^|\n\r]+)", wikitext)
    classes_match = re.search(r"\|Klassen\s*=\s*([^|\n\r]+)", wikitext)
    type_match = re.search(r"\|(?:Waffenart|Rüstungstyp)\s*=\s*([^|\n\r]+)", wikitext)
    image_match = re.search(r"\|IG-Bild\s*=\s*([^|\n\r]+)", wikitext)
    
    data["level"] = clean_wiki_markup(level_match.group(1)) if level_match else None
    data["classes"] = clean_wiki_markup(classes_match.group(1)) if classes_match else None
    data["type"] = clean_wiki_markup(type_match.group(1)) if type_match else None
    data["main_image"] = get_image_url(image_match.group(1).strip()) if image_match else None
    
    # Costes y Materiales de mejora (Upgrade)
    kosten = dict(re.findall(r"\|Kosten(\d+)\s*=\s*([^|\n\r]+)", wikitext))
    
    upgrades = []
    for i in range(1, 10):
        lvl_key = str(i)
        target_lvl_str = f"+{i}"
        
        # Filtrar si el usuario pidió un nivel específico (ej: +9)
        if target_plus is not None and target_plus != i:
            continue
            
        cost = kosten.get(lvl_key, "0").strip()
        
        # Buscar items de mejora: Upgradeitem-1-X, Upgradeitem-2-X
        mats_raw = re.findall(rf"\|Upgradeitem-\d+-{lvl_key}\s*=\s*([^\n\r|]+)", wikitext)
        materials_parsed = []
        for mr in mats_raw:
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
    """
    Parsea la plantilla Quest/Layout
    """
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
    """
    Parsea la plantilla Monster/Layout y Metin/Layout
    """
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
