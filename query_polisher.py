import json
import re
import unicodedata
import difflib
import sys

sys.stdout.reconfigure(encoding='utf-8')

CATALOG_PATH = "d:\\wm2\\catalog_index.json"

# Diccionario de jerga gamer de Metin2 y contracciones comunes
METIN2_SLANG = {
    "vms": "Espada Luna Llena",
    "luna": "Espada Luna Llena",
    "llna": "Espada Luna Llena",
    "fms": "Espada Luna Llena",
    "hierro": "Hoja de Hierro Rojo",
    "rib": "Hoja de Hierro Rojo",
    "biolo": "Biologe",
    "biologo": "Biologe",
    "enve": "Espada Envenenada",
    "venenosa": "Espada Envenenada",
    "eves": "Pendientes de Ébano",
    "ebanos": "Pendientes de Ébano",
    "platas": "Brazalete de Plata",
    "orkzahn": "Orkzahn",
    "dientes": "Orkzahn",
    "diente": "Orkzahn",
    "mats": "materiales",
    "mat": "materiales",
    "up": "subir",
    "mejora": "subir"
}

# Normalización de números y niveles (+0 a +9)
PLUS_MAP = {
    "cero": 0, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, 
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nuebe": 9, "nueve": 9
}

def clean_text(text):
    """Elimina tildes, signos raros y convierte a minúsculas limpias"""
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r"[^\w\s\+]", " ", text)
    return text.strip()

class QueryPolisher:
    def __init__(self, catalog_path):
        with open(catalog_path, "r", encoding="utf-8") as f:
            self.catalog = json.load(f)
            
        # Creamos índice rápido de búsqueda (español y alemán)
        self.search_index = {}
        for de_name, info in self.catalog.items():
            # indexar alemán
            clean_de = clean_text(de_name)
            self.search_index[clean_de] = de_name
            
            # indexar español si existe
            es_name = info.get("title_es")
            if es_name:
                clean_es = clean_text(es_name)
                self.search_index[clean_es] = de_name

    def polish(self, raw_query):
        original = raw_query
        normalized = clean_text(raw_query)
        words = normalized.split()

        # 1. Detección de nivel objetivo (+X o "pa nueve")
        target_plus = None
        match_plus = re.search(r"\+(\d)", normalized)
        if match_plus:
            target_plus = int(match_plus.group(1))
        else:
            for word, val in PLUS_MAP.items():
                if word in words:
                    target_plus = val
                    break

        # 2. Expansión de jerga / Slang
        expanded_words = []
        for w in words:
            if w in METIN2_SLANG:
                expanded_words.append(METIN2_SLANG[w])
            else:
                expanded_words.append(w)
        processed_query = " ".join(expanded_words)

        # 3. Detección de Intención
        intent = "general_info"
        if any(w in normalized for w in ["pide", "material", "mats", "subir", "up", "coste", "yang", "nuebe", "nueve"]) or target_plus is not None:
            intent = "upgrade_requirements"
        elif any(w in normalized for w in ["donde", "dropea", "suelta", "quien"]):
            intent = "drop_location"
        elif any(w in normalized for w in ["mision", "quest", "biolo", "recompensa"]):
            intent = "quest_info"

        # 4. Fuzzy Matching contra el catálogo de 3.400 entidades
        # Buscamos coincidencias aproximadas
        candidate_keys = list(self.search_index.keys())
        
        # Probar con la frase completa y con combinaciones de palabras
        best_match = None
        highest_score = 0
        
        # Eliminar palabras vacías (stopwords)
        stopwords = {"q", "que", "pide", "pa", "para", "la", "el", "los", "las", "subir", "a", "de", "en", "como", "donde", "mision"}
        content_words = [w for w in clean_text(processed_query).split() if w not in stopwords and not w.isdigit()]
        cleaned_entity_query = " ".join(content_words)

        # Búsqueda difusa (Fuzzy Matching)
        matches = difflib.get_close_matches(cleaned_entity_query, candidate_keys, n=3, cutoff=0.45)
        if matches:
            best_key = matches[0]
            best_match = self.search_index[best_key]
        else:
            # Búsqueda por subpalabras si falló la frase
            for word in content_words:
                sub_matches = difflib.get_close_matches(word, candidate_keys, n=1, cutoff=0.6)
                if sub_matches:
                    best_match = self.search_index[sub_matches[0]]
                    break

        entity_info = self.catalog.get(best_match) if best_match else None
        
        return {
            "query_original": original,
            "intencion": intent,
            "nivel_objetivo": f"+{target_plus}" if target_plus is not None else "Todos (+0 a +9)",
            "entidad_oficial_de": best_match,
            "nombre_es": entity_info.get("title_es") if entity_info else None,
            "tipo_entidad": entity_info.get("type") if entity_info else None
        }

def test():
    polisher = QueryPolisher(CATALOG_PATH)
    
    # Ejemplos de consultas sucias / mal escritas
    test_queries = [
        "q pide pa nuebe la espad bambu",
        "donde cae el vms",
        "mision biolo 30 dientes orco",
        "mats pa subr armadra dragon +7",
        "kien suelta el hierro rojo"
    ]
    
    print("=" * 70)
    print("DEMOSTRACIÓN: PULIDO DE CONSULTAS SUCIAS Y CON ERRORES")
    print("=" * 70)
    
    for q in test_queries:
        res = polisher.polish(q)
        print(f"\n[ENTRADA SUCIA]: \"{res['query_original']}\"")
        print(f" -> Intención:        {res['intencion']}")
        print(f" -> Nivel detectado:  {res['nivel_objetivo']}")
        print(f" -> Objeto Oficial:   {res['entidad_oficial_de']} ({res['nombre_es'] or 'Sin trad direct'})")
        print(f" -> Categoría/Tipo:   {res['tipo_entidad']}")

if __name__ == "__main__":
    test()
