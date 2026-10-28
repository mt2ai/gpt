import json
import re
import unicodedata
import difflib
import os
import urllib.parse

from .wiki_client import get_page_content
from .parser_layouts import parse_equipment_layout, parse_quest_layout, parse_monster_layout

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")

CATALOG_FILE = os.path.join(DATA_DIR, "catalog_index.json")
SLANG_FILE = os.path.join(DATA_DIR, "slang_dictionary.json")

def normalize_string(text):
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r"[^\w\s\+]", " ", text)
    return " ".join(text.split())

class Metin2Engine:
    def __init__(self):
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            self.catalog = json.load(f)
            
        with open(SLANG_FILE, "r", encoding="utf-8") as f:
            self.slang = json.load(f)
            
        # Generar índice semántico y fonético
        self.search_index = {}
        for de_name, info in self.catalog.items():
            self.search_index[normalize_string(de_name)] = de_name
            es_name = info.get("title_es")
            if es_name:
                self.search_index[normalize_string(es_name)] = de_name
                
        # Agregar jerga al índice directo
        for slang_word, target_de in self.slang.items():
            self.search_index[normalize_string(slang_word)] = target_de

    def resolve_query(self, user_query):
        norm_query = normalize_string(user_query)
        words = norm_query.split()
        
        # 1. Detectar si especificó un nivel (+0 a +9 o palabras)
        target_plus = None
        match_plus = re.search(r"\+(\d)", norm_query)
        if match_plus:
            target_plus = int(match_plus.group(1))
        else:
            word_num_map = {
                "cero": 0, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, 
                "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nuebe": 9, "nueve": 9
            }
            for w, n in word_num_map.items():
                if w in words:
                    target_plus = n
                    break

        # 2. Identificar la entidad oficial usando coincidencia exacta y difusa
        matched_de_title = None
        
        # Búsqueda directa por frase o jerga
        if norm_query in self.search_index:
            matched_de_title = self.search_index[norm_query]
        else:
            # Revisar jerga ordenada por longitud (las frases más largas primero: ej "biologo 30" antes que "orco")
            sorted_slang = sorted(self.slang.items(), key=lambda x: len(x[0]), reverse=True)
            for slang_term, de_title in sorted_slang:
                if slang_term in norm_query:
                    matched_de_title = de_title
                    break
                    
        # Si aún no coincide, aplicar Fuzzy Matching quitando stopwords
        if not matched_de_title:
            stopwords = {"q", "que", "pide", "pa", "para", "la", "el", "los", "las", "subir", "a", "de", "en", "como", "donde", "mision", "dropea", "cae", "suelta"}
            meaningful_words = [w for w in words if w not in stopwords and not w.isdigit()]
            query_core = " ".join(meaningful_words)
            
            keys = list(self.search_index.keys())
            matches = difflib.get_close_matches(query_core, keys, n=1, cutoff=0.5)
            if matches:
                matched_de_title = self.search_index[matches[0]]
            else:
                # Probar palabra por palabra
                for mw in meaningful_words:
                    sub_m = difflib.get_close_matches(mw, keys, n=1, cutoff=0.65)
                    if sub_m:
                        matched_de_title = self.search_index[sub_m[0]]
                        break

        if not matched_de_title:
            return {
                "success": False,
                "message": f"No pude encontrar el objeto o misión correspondiente a tu búsqueda: '{user_query}'."
            }

        # 3. Descargar wikitext y parsear según el tipo
        entity_info = self.catalog.get(matched_de_title, {})
        ent_type = entity_info.get("type", "unknown")
        title_es = entity_info.get("title_es") or matched_de_title
        
        wikitext = get_page_content(matched_de_title)
        if not wikitext:
            return {
                "success": False,
                "message": f"Se identificó '{title_es}' ({matched_de_title}), pero no fue posible cargar el artículo oficial en la wiki."
            }

        # 4. Extracción de datos determinista
        parsed_data = {}
        wiki_url = f"https://de-wiki.metin2.gameforge.com/index.php/{urllib.parse.quote(matched_de_title)}"
        
        if ent_type in ["weapon", "armor", "helmet", "shield", "earring", "bracelet", "necklace", "shoes", "belt", "talisman"]:
            parsed_data = parse_equipment_layout(wikitext, target_plus=target_plus)
            category_label = "Equipamiento"
        elif ent_type == "quest":
            parsed_data = parse_quest_layout(wikitext)
            category_label = "Misión"
        elif ent_type in ["monster", "boss", "metin"]:
            parsed_data = parse_monster_layout(wikitext)
            category_label = "Monstruo / Jefe"
        else:
            category_label = "Objeto"
            parsed_data = {"description": wikitext[:600]}

        return {
            "success": True,
            "query_original": user_query,
            "entity": {
                "title_de": matched_de_title,
                "title_es": title_es,
                "type": ent_type,
                "category_label": category_label,
                "wiki_url": wiki_url
            },
            "target_plus": target_plus,
            "data": parsed_data
        }
