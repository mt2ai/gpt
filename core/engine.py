import json
import re
import unicodedata
import difflib
import os
import random
import urllib.parse

from .wiki_client import get_page_content
from .parser_layouts import parse_equipment_layout, parse_quest_layout, parse_monster_layout

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")

CATALOG_FILE = os.path.join(DATA_DIR, "catalog_index.json")
SLANG_FILE = os.path.join(DATA_DIR, "slang_dictionary.json")

# ── Respuestas conversacionales ─────────────────────────────────────────────

CONVERSATIONAL_INTENTS = [
    {
        "name": "greeting",
        "patterns": [
            r"\b(hola|buenas|hey|ey|eyyy|saludos|buenos dias|buenas tardes|buenas noches|hi|hello|que tal|que onda|que hubo|ke tal|ktal)\b"
        ],
        "responses": [
            "¡Hola! 👋 Soy el **Metin2 Oracle**, tu asistente oficial de Metin2.\n\nPuedo ayudarte con:\n- 🗡️ Materiales de mejora de armas y armaduras\n- 📜 Guías de misiones (Biólogo, Pescador, etc.)\n- 🌙 Información de drops de monstruos y jefes\n- 💎 Cualquier cosa del juego que quieras consultar\n\n¿Qué necesitas saber?",
            "¡Buenas! 🔥 Estoy listo para ayudarte con todo lo de Metin2.\n\nSolo escribe lo que necesitas, puedes escribirlo con faltas o en argot gamer (ej: *\"q pide pa nueve la enve\"*, *\"donde dropea el vms\"*).\n\n¿En qué te ayudo?",
        ]
    },
    {
        "name": "farewell",
        "patterns": [
            r"\b(adios|chao|bye|hasta luego|nos vemos|ciao|hasta pronto|me voy|cuídate|gracias y adios)\b"
        ],
        "responses": [
            "¡Hasta luego! ⚔️ Que el Yang te acompañe en Metin2. Vuelve cuando necesites info.",
            "¡Chao! 🌙 Suerte en el server. Cualquier duda, aquí estaré.",
        ]
    },
    {
        "name": "thanks",
        "patterns": [
            r"\b(gracias|grax|grac|muchas gracias|ty|thx|thanks|mil gracias|excelente|perfecto|genial|que bueno|de puta madre|chido|chevere)\b"
        ],
        "responses": [
            "¡De nada! 😊 Para eso estoy. ¿Algo más que necesites de Metin2?",
            "¡Con gusto! ⚔️ Si tienes otra duda, solo pregunta.",
            "¡Claro que sí! 🎮 ¿Hay algo más en lo que pueda ayudarte?",
        ]
    },
    {
        "name": "who_are_you",
        "patterns": [
            r"\b(quien eres|que eres|como te llamas|que puedes hacer|para que sirves|que sabes|en que me ayudas|cuales son tus capacidades)\b"
        ],
        "responses": [
            "Soy el **Metin2 Oracle** 🔮, un asistente especializado en Metin2.\n\nExtrae información **directamente de la wiki oficial alemana** (la más completa y actualizada) en tiempo real.\n\n**Puedo responder sobre:**\n- 🗡️ Mejoras de armas y armaduras (+0 a +9)\n- 📜 Misiones: Biólogo, Pescador, Guerrero, etc.\n- 👹 Drops de monstruos, jefes y metins\n- 💰 Costos en Yang y materiales necesarios\n- 🎨 Iconos reales del juego\n\nEscribe tu consulta con jerga o faltas, te entiendo igual 😄",
        ]
    },
    {
        "name": "how_are_you",
        "patterns": [
            r"\b(como estas|como andas|todo bien|como te va|bien y tu|que hay|que cuentas)\b"
        ],
        "responses": [
            "¡Todo bien por aquí, listo para consultas! 💪 ¿Qué necesitas saber de Metin2?",
            "¡Perfecto y tú! 😄 Cuéntame qué necesitas del juego.",
        ]
    },
    {
        "name": "insult_or_test",
        "patterns": [
            r"\b(tonto|estupido|idiota|malo|inutil|no sirves|eres una mierda|test|prueba|hola mundo)\b"
        ],
        "responses": [
            "Soy un oráculo, no me ofendo tan fácil 😄 ¿Necesitas algo de Metin2?",
            "Jaja, me das duro 😅 Pero bueno, ¿en qué te ayudo con Metin2?",
        ]
    },
    {
        "name": "joke",
        "patterns": [
            r"\b(cuéntame un chiste|dime un chiste|chiste|bromea|algo divertido)\b"
        ],
        "responses": [
            "¿Por qué el guerrero de Metin2 nunca llega tarde? ⚔️\n\nPorque siempre va al **servidor correcto**. 😄\n\n¿Pregunta algo del juego y te respondo en serio!",
        ]
    },
]

def detect_conversational_intent(norm_query):
    """
    Detecta si la consulta es conversacional (saludo, despedida, etc.)
    Retorna (intent_name, response) o (None, None).
    """
    for intent in CONVERSATIONAL_INTENTS:
        for pattern in intent["patterns"]:
            if re.search(pattern, norm_query):
                return intent["name"], random.choice(intent["responses"])
    return None, None

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
        self.de_to_es = {}
        for de_name, info in self.catalog.items():
            self.search_index[normalize_string(de_name)] = de_name
            es_name = info.get("title_es")
            if es_name:
                self.search_index[normalize_string(es_name)] = de_name
                self.de_to_es[de_name] = es_name
            else:
                self.de_to_es[de_name] = de_name
                
        # Agregar jerga al índice directo
        for slang_word, target_de in self.slang.items():
            self.search_index[normalize_string(slang_word)] = target_de

        # Memoria de conversación por sesión
        # session_id -> { "last_entity": "Giftschwert", "last_query": "..." }
        self.sessions = {}

    def translate_raw_names(self, text):
        """
        Traduce nombres de monstruos, cofres y metins en textos libres de drop
        """
        if not text:
            return ""
        # Reemplazar términos comunes de estructura
        text = text.replace("Monster:", "Monstruos:").replace("Truhen:", "Cofres:").replace("Sonstiges:", "Otros:")
        # Ordenar traducciones por longitud descendente para evitar colisiones de subcadenas
        sorted_pairs = sorted(self.de_to_es.items(), key=lambda x: len(x[0]), reverse=True)
        for de_name, es_name in sorted_pairs:
            if len(de_name) > 3 and de_name in text:
                text = text.replace(de_name, es_name)
        return text

    def resolve_query(self, user_query, session_id="default"):
        norm_query = normalize_string(user_query)
        words = norm_query.split()

        # 0. Detectar intención conversacional (saludos, despedidas, etc.)
        intent_name, conv_response = detect_conversational_intent(norm_query)
        if intent_name:
            return {
                "success": True,
                "type": "conversational",
                "intent": intent_name,
                "message": conv_response
            }

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

        # 2. Identificar la entidad oficial
        matched_de_title = None
        
        # Búsqueda directa por frase o jerga
        if norm_query in self.search_index:
            matched_de_title = self.search_index[norm_query]
        else:
            # Revisar jerga ordenada por longitud (las frases más largas primero)
            sorted_slang = sorted(self.slang.items(), key=lambda x: len(x[0]), reverse=True)
            for slang_term, de_title in sorted_slang:
                if slang_term in norm_query:
                    matched_de_title = de_title
                    break

        # Búsqueda difusa eliminando stopwords
        if not matched_de_title:
            stopwords = {
                "q", "que", "pide", "pa", "para", "la", "el", "los", "las", "subir", "a", "de", "en", 
                "como", "donde", "mision", "dropea", "cae", "suelta", "quien", "consigo", "da", "consigue",
                "necesito", "una", "un", "los", "las", "y", "o", "cuanto", "yang", "materiales", "dame"
            }
            meaningful_words = [w for w in words if w not in stopwords and not w.isdigit()]
            query_core = " ".join(meaningful_words)
            
            if query_core:
                keys = list(self.search_index.keys())
                matches = difflib.get_close_matches(query_core, keys, n=1, cutoff=0.5)
                if matches:
                    matched_de_title = self.search_index[matches[0]]
                else:
                    for mw in meaningful_words:
                        sub_m = difflib.get_close_matches(mw, keys, n=1, cutoff=0.65)
                        if sub_m:
                            matched_de_title = self.search_index[sub_m[0]]
                            break

        # 3. MEMORIA DE CONVERSACIÓN: Si no detectó una entidad nueva, recurrir a la última entidad activa
        session = self.sessions.get(session_id, {})
        if not matched_de_title:
            if "last_entity" in session:
                matched_de_title = session["last_entity"]
                print(f"[Memory] Usando contexto previo para sesión '{session_id}': {matched_de_title}")

        if not matched_de_title:
            return {
                "success": False,
                "message": (
                    f"🤔 No encontré nada relacionado con **\"{user_query}\"** en la wiki oficial.\n\n"
                    "Intenta ser más específico, por ejemplo:\n"
                    "- *\"materiales espada bambu +9\"*\n"
                    "- *\"donde dropea el vms\"*\n"
                    "- *\"mision biologo 30 dientes\"*"
                )
            }

        # Guardar en memoria de sesión
        self.sessions[session_id] = {
            "last_entity": matched_de_title,
            "last_query": user_query
        }

        # 4. Descargar wikitext y parsear
        entity_info = self.catalog.get(matched_de_title, {})
        ent_type = entity_info.get("type", "unknown")
        title_es = entity_info.get("title_es") or self.de_to_es.get(matched_de_title, matched_de_title)
        
        wikitext = get_page_content(matched_de_title)
        if not wikitext:
            return {
                "success": False,
                "message": f"Se identificó '{title_es}', pero no fue posible cargar el artículo oficial en la wiki."
            }

        parsed_data = {}
        wiki_url = f"https://de-wiki.metin2.gameforge.com/index.php/{urllib.parse.quote(matched_de_title)}"
        
        if ent_type in ["weapon", "armor", "helmet", "shield", "earring", "bracelet", "necklace", "shoes", "belt", "talisman"]:
            parsed_data = parse_equipment_layout(wikitext, target_plus=target_plus)
            category_label = "Equipamiento"
            if parsed_data.get("drops_raw"):
                parsed_data["drops_raw"] = self.translate_raw_names(parsed_data["drops_raw"])
        elif ent_type == "quest":
            parsed_data = parse_quest_layout(wikitext)
            category_label = "Misión"
        elif ent_type in ["monster", "boss", "metin"]:
            parsed_data = parse_monster_layout(wikitext)
            category_label = "Monstruo / Jefe"
            if parsed_data.get("drops_text"):
                parsed_data["drops_text"] = self.translate_raw_names(parsed_data["drops_text"])
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
