import json
import re
import unicodedata
import difflib
import os
import random
import urllib.parse

from .wiki_client import get_page_content
from .parser_layouts import parse_equipment_layout, parse_quest_layout, parse_monster_layout
from .llm import GroqLLM

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "data")

CATALOG_FILE = os.path.join(DATA_DIR, "catalog_index.json")
SLANG_FILE = os.path.join(DATA_DIR, "slang_dictionary.json")

# ── Respuestas conversacionales de respaldo (si no hay LLM activo) ───────────

CONVERSATIONAL_INTENTS = [
    {
        "name": "greeting",
        "patterns": [
            r"\b(hola|buenas|hey|ey|eyyy|saludos|buenos dias|buenas tardes|buenas noches|hi|hello|que tal|que onda|que hubo|ke tal|ktal)\b"
        ],
        "responses": [
            "¡Hola! 👋 Soy el **Metin2 Oracle**, tu asistente oficial de Metin2.\n\nPuedo ayudarte con:\n- 🗡️ Materiales de mejora de armas y armaduras\n- 📜 Guías de misiones (Biólogo, Pescador, etc.)\n- 🌙 Información de drops de monstruos y jefes\n- 💎 Cualquier duda o guía del juego que quieras consultar\n\n¿Qué necesitas saber?",
            "¡Buenas! 🔥 Estoy listo para ayudarte con todo lo de Metin2.\n\nSolo escribe lo que necesitas, puedes escribirlo con faltas o en argot gamer (ej: *\"q pide pa nueve la enve\"*, *\"donde dropea el vms\"*, *\"cuantas misiones del biologo hay\"*).\n\n¿En qué te ayudo?",
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
            "Soy el **Metin2 Oracle** 🔮, tu oráculo inteligente para Metin2 con tecnología IA y datos oficiales de la wiki.\n\n**Puedo responder sobre:**\n- 🗡️ Mejoras de armas y armaduras (+0 a +9)\n- 📜 Misiones: Biólogo, Pescador, Caballo, etc.\n- 👹 Drops de monstruos, jefes y metins\n- 💰 Costos en Yang y materiales necesarios\n- 💡 Guías de leveo, doctrinas, alquimia y atributos\n\nPregúntame lo que quieras con cualquier jerga gamer 😄",
        ]
    },
]

def detect_conversational_intent(norm_query):
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

        # Inicializar cliente LLM de Groq
        self.llm = GroqLLM()

        # Memoria de conversación por sesión
        # session_id -> { "messages": [...], "last_entity": "Giftschwert" }
        self.sessions = {}

    def translate_raw_names(self, text):
        if not text:
            return ""
        text = text.replace("Monster:", "Monstruos:").replace("Truhen:", "Cofres:").replace("Sonstiges:", "Otros:")
        text = text.replace("Level", "Nivel").replace("Klassen abhängig", "según la clase").replace("abhängig", "según la clase")
        text = text.replace("Klassen", "Clases").replace("Belohnung", "Recompensa").replace("Lösung", "Solución")
        sorted_pairs = sorted(self.de_to_es.items(), key=lambda x: len(x[0]), reverse=True)
        for de_name, es_name in sorted_pairs:
            if len(de_name) > 3 and de_name in text:
                text = text.replace(de_name, es_name)
        return text

    def translate_field_with_ai(self, text):
        if not text:
            return ""
        translated = self.translate_raw_names(text)
        if self.llm.is_available() and len(translated) > 4:
            return self.llm.translate_to_spanish(translated)
        return translated

    def _record_session_message(self, session_id, role, content):
        if session_id not in self.sessions:
            self.sessions[session_id] = {"messages": [], "last_entity": None}
        messages = self.sessions[session_id]["messages"]
        messages.append({"role": role, "content": content})
        # Mantener solo las últimas 12 entradas
        if len(messages) > 12:
            self.sessions[session_id]["messages"] = messages[-12:]

    def resolve_query(self, user_query, session_id="default"):
        norm_query = normalize_string(user_query)
        words = norm_query.split()

        if session_id not in self.sessions:
            self.sessions[session_id] = {"messages": [], "last_entity": None}
        session = self.sessions[session_id]

        # 1. Detectar si la consulta es una pregunta o frase en lenguaje natural
        is_natural_question = bool(
            "?" in user_query or len(words) >= 4 or re.search(
                r"\b(sabes|existe|puede|puedo|pueden|podemos|tener|tengo|tienen|se puede|como|cómo|que|qué|cual|cuál|cuales|cuáles|por que|por qué|porque|donde|dónde|cuando|cuándo|quien|quién|cuanto|cuánto|cuantos|cuántos|cuantas|cuántas|hay|sirve|funciona|pasa|recomiend|consejo|consejos|guia|guía|fallo|fallar|probabilidad|mascota|mascotas|pet|pets|combinar|diferencia|compara|alquimia|caballo|levear|leveo)\b",
                norm_query
            )
        )

        # 2. Detectar si se pregunta por una mejora específica (+0 a +9) o materiales
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

        # 3. Saludos o cortesía breve
        intent_name, conv_response = detect_conversational_intent(norm_query)
        if intent_name and len(words) <= 3:
            if self.llm.is_available():
                history = session.get("messages", [])
                llm_reply = self.llm.generate_response(user_query, history=history)
                if llm_reply:
                    self._record_session_message(session_id, "user", user_query)
                    self._record_session_message(session_id, "assistant", llm_reply)
                    return {
                        "success": True,
                        "type": "conversational",
                        "message": llm_reply
                    }
            return {
                "success": True,
                "type": "conversational",
                "intent": intent_name,
                "message": conv_response
            }

        # 4. Identificar entidad oficial si el usuario la nombra específicamente
        matched_de_title = None
        
        # Búsqueda directa por frase exacta o jerga
        if norm_query in self.search_index:
            matched_de_title = self.search_index[norm_query]
        else:
            # Buscar coincidencia exacta de jerga conocida (ordenada de mayor a menor longitud)
            sorted_slang = sorted(self.slang.items(), key=lambda x: len(x[0]), reverse=True)
            for slang_term, de_title in sorted_slang:
                # La jerga debe estar como palabra completa o frase contenida
                if re.search(rf"\b{re.escape(slang_term)}\b", norm_query):
                    matched_de_title = de_title
                    break

        # Búsqueda difusa: SOLO si es una consulta corta (1 a 3 palabras) y NO es una pregunta abierta
        if not matched_de_title and not is_natural_question and len(words) <= 3:
            stopwords = {
                "q", "que", "pide", "pa", "para", "la", "el", "los", "las", "subir", "a", "de", "en", 
                "como", "donde", "mision", "misiones", "dropea", "cae", "suelta", "quien", "consigo", "da", "consigue",
                "necesito", "una", "un", "los", "las", "y", "o", "cuanto", "cuantos", "cuantas", "yang", "materiales", "dame"
            }
            meaningful_words = [w for w in words if w not in stopwords and not w.isdigit()]
            query_core = " ".join(meaningful_words)
            if query_core:
                keys = list(self.search_index.keys())
                matches = difflib.get_close_matches(query_core, keys, n=1, cutoff=0.7)
                if matches:
                    matched_de_title = self.search_index[matches[0]]

        # Si es una pregunta natural y NO pide explícitamente materiales de mejora ni ficha de objeto:
        # Dejar que el LLM responda con su conocimiento conversacional sin forzar fichas irrelevantes
        is_asking_for_card = bool(target_plus is not None or any(w in words for w in ["pide", "materiales", "mats", "stats", "atributos", "tabla"]))
        if is_natural_question and self.llm.is_available() and not is_asking_for_card:
            history = session.get("messages", [])
            llm_reply = self.llm.generate_response(user_query, history=history)
            if llm_reply:
                self._record_session_message(session_id, "user", user_query)
                self._record_session_message(session_id, "assistant", llm_reply)
                return {
                    "success": True,
                    "type": "conversational",
                    "message": llm_reply
                }

        # Memoria de conversación: usar última entidad si la consulta es un pronombre o contexto ("y a +9?", "donde cae?")
        if not matched_de_title and session.get("last_entity"):
            if any(w in words for w in ["donde", "cae", "dropea", "subir", "pide", "mats", "yang", "coste", "nivel"]) or target_plus is not None:
                matched_de_title = session["last_entity"]

        # Si aún no se encontró entidad pero hay LLM disponible: responder de forma conversacional con el LLM
        if not matched_de_title and self.llm.is_available():
            history = session.get("messages", [])
            llm_reply = self.llm.generate_response(user_query, history=history)
            if llm_reply:
                self._record_session_message(session_id, "user", user_query)
                self._record_session_message(session_id, "assistant", llm_reply)
                return {
                    "success": True,
                    "type": "conversational",
                    "message": llm_reply
                }

        # Si no hay entidad ni LLM
        if not matched_de_title:
            return {
                "success": False,
                "message": (
                    f"🤔 No encontré información específica sobre **\"{user_query}\"**.\n\n"
                    "Puedes preguntar cosas como:\n"
                    "- *\"cuántas misiones del biólogo hay\"*\n"
                    "- *\"qué pide para nueve la enve\"*\n"
                    "- *\"dónde cae el vms\"*\n"
                    "- *\"cómo sacar caballo armado\"*"
                )
            }

        # Guardar en memoria de sesión
        session["last_entity"] = matched_de_title

        # Obtener datos oficiales de la wiki
        entity_info = self.catalog.get(matched_de_title, {})
        ent_type = entity_info.get("type", "unknown")
        title_es = entity_info.get("title_es") or self.de_to_es.get(matched_de_title, matched_de_title)
        wiki_url = f"https://de-wiki.metin2.gameforge.com/index.php/{urllib.parse.quote(matched_de_title)}"

        parsed_data = {}
        category_label = "Objeto"
        wikitext = ""

        try:
            wikitext = get_page_content(matched_de_title)
        except Exception as e:
            print(f"[Engine] Error al obtener wiki content: {e}")

        if wikitext:
            if ent_type in ["weapon", "armor", "helmet", "shield", "earring", "bracelet", "necklace", "shoes", "belt", "talisman"]:
                parsed_data = parse_equipment_layout(wikitext, target_plus=target_plus)
                category_label = "Equipamiento"
                if parsed_data.get("drops_raw"):
                    parsed_data["drops_raw"] = self.translate_field_with_ai(parsed_data["drops_raw"])
                if parsed_data.get("upgrades"):
                    for up in parsed_data["upgrades"]:
                        for m in up.get("materials", []):
                            m["display"] = self.translate_raw_names(m.get("display"))
            elif ent_type == "quest":
                parsed_data = parse_quest_layout(wikitext)
                category_label = "Misión"
                if parsed_data.get("rewards_text"):
                    parsed_data["rewards_text"] = self.translate_field_with_ai(parsed_data["rewards_text"])
                if parsed_data.get("solution"):
                    parsed_data["solution"] = self.translate_field_with_ai(parsed_data["solution"])
                if parsed_data.get("items"):
                    for it in parsed_data["items"]:
                        it["name_es"] = self.translate_raw_names(it.get("name_es") or it.get("name"))
                        it["display"] = self.translate_raw_names(it.get("display"))
            elif ent_type in ["monster", "boss", "metin"]:
                parsed_data = parse_monster_layout(wikitext)
                category_label = "Monstruo / Jefe"
                if parsed_data.get("drops_text"):
                    parsed_data["drops_text"] = self.translate_field_with_ai(parsed_data["drops_text"])
            else:
                category_label = "Objeto"
                desc_trans = self.translate_field_with_ai(wikitext[:600])
                parsed_data = {"description": desc_trans}

        # Si el LLM está activo, generar explicación natural enriquecida con los datos oficiales
        ai_message = None
        if self.llm.is_available():
            wiki_summary = f"Entidad: {title_es} ({matched_de_title}) - Categoría: {category_label}\n"
            if target_plus is not None:
                wiki_summary += f"Nivel consultado: +{target_plus}\n"
            if parsed_data.get("upgrades"):
                wiki_summary += f"Tabla de mejoras disponible para {len(parsed_data['upgrades'])} niveles.\n"
            if parsed_data.get("drops_raw"):
                wiki_summary += f"Drops / Obtención: {parsed_data['drops_raw']}\n"
            if parsed_data.get("rewards_text"):
                wiki_summary += f"Recompensas: {parsed_data['rewards_text']}\n"

            history = session.get("messages", [])
            ai_message = self.llm.generate_response(user_query, history=history, wiki_context=wiki_summary)
            if ai_message:
                self._record_session_message(session_id, "user", user_query)
                self._record_session_message(session_id, "assistant", ai_message)

        # Si tenemos tarjeta parseada
        if parsed_data:
            return {
                "success": True,
                "type": "wiki_card_with_ai" if ai_message else "wiki_card",
                "message": ai_message or "",
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

        # Si falló la wiki pero tenemos IA
        if ai_message:
            return {
                "success": True,
                "type": "conversational",
                "message": ai_message
            }

        return {
            "success": False,
            "message": f"Se identificó '{title_es}', pero la wiki oficial no se encuentra disponible temporalmente."
        }

