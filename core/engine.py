import json
import re
import unicodedata
import difflib
import os
import random
import urllib.parse

from .wiki_client import get_page_content, fetch_es_wiki_grounding
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

METIN2_TERMS = {
    # Juego / General
    "metin", "metin2", "yang", "won", "dss", "fks", "pvm", "pvp", "dopes", "dopear", "dopada",
    "ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "server", "servidor", "gameforge",
    # Mecánicas y Sistemas
    "alquimia", "estola", "estolas", "cinturon", "cinturones", "talisman", "talismanes",
    "mascota", "mascotas", "pet", "pets", "incubadora", "huevo", "huevos",
    "caballo", "montura", "monturas", "establo", "medalla", "medallas",
    "biologo", "chaegirab", "seon-pyeong", "seon", "pyeong", "uriel", "baek-go", "baek",
    "herrero", "bendi", "bendicion", "pergamino", "pergaminos", "manual",
    "habilidad", "habilidades", "master", "gran master", "perfect master", "piedra alma", "piedras alma",
    "doctrina", "corporal", "mental", "magia negra", "armamento", "asesino", "arquero",
    "luz", "dragon", "licano", "guerrero", "sura", "ninja", "chaman", "shaman",
    # Zonas y Mazmorras
    "aldea", "mapa1", "mapa2", "valle", "desierto", "sohan", "fuego", "doyyumhwan",
    "gruta", "grotto", "atlantida", "sd1", "sd2", "sd3", "arana", "aranas",
    "torre", "demonios", "catacumbas", "purgatorio", "nemere", "razador", "meley",
    "jotun", "thrym", "hidra", "beran", "setau", "azrael", "segador",
    # Misiones y Drops
    "levear", "leveo", "farmear", "farmeo", "drop", "dropea", "dropean", "cae", "tira", "suelta",
    "dientes", "maldicion", "recuerdos", "zelkova", "tugyi", "tablillas", "gemas", "joyas",
    "orco", "orcos", "lacayo", "arquero salvaje", "vms", "enve", "rib", "fms", "ebanos",
    "espada", "armadura", "casco", "escudo", "zapatos", "pendientes", "brazalete", "collar"
}

ES_SEARCH_ALIASES = {
    "sd1": "Caverna de arañas 1",
    "sd2": "Caverna de arañas 2",
    "sd3": "Caverna de arañas 3",
    "vms": "Espada Luna Llena",
    "luna": "Espada Luna Llena",
    "enve": "Espada Envenenada",
    "rib": "Hierro Rojo",
    "hierro": "Hierro Rojo",
    "ebanos": "Pendientes de Ébano",
    "grotto": "Gruta del Exilio",
    "gruta": "Gruta del Exilio",
    "torre": "Torre Demoníaca",
    "biolo": "Biólogo Chaegirab",
    "biologo": "Biólogo Chaegirab",
    "chaegirab": "Biólogo Chaegirab",
    "aura": "Aura de espada",
    "cuerpo fuerte": "Cuerpo Fuerte",
    "beran": "Beran-Setaou",
    "setau": "Beran-Setaou",
    "segador": "Segador de la Muerte",
    "azrael": "Azrael",
    "razador": "Razador",
    "nemere": "Nemere",
    "meley": "Reina Meley",
    "jotun": "Jotun Thrym",
    "hidra": "Hidra",
    "caballo": "Misiones de Caballo",
    "alquimia": "Alquimia",
    "dientes": "Dientes de Orco",
    "maldicion": "Libro Maldición",
    "recuerdos": "Recuerdo del Demonio",
    "zelkova": "Ramas de Zelkova",
    "tugyi": "Tablillas de Tugyi",
    "rey llama": "Rey Llama",
    "jefe orco": "Jefe Orco",
    "nueve colas": "Nueve Colas",
    "tortuga": "Tortuga Gigante",
    "fantasma tigre": "Fantasma Tigre Amarillo"
}

QUERY_STOPWORDS = {
    "donde", "sale", "el", "la", "los", "las", "un", "una", "de", "del", "en", "como", "que", "es",
    "para", "mi", "pj", "puede", "tener", "cuanto", "cuantos", "cuantas", "dame", "consejos",
    "guia", "matar", "sacar", "hacer", "subir", "conseguir", "dropea", "cae", "tira", "suelta",
    "pide", "mats", "materiales", "hay", "sirve", "funciona", "se", "por", "favor", "nivel", "lvl"
}

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

    def extract_es_search_term(self, query, matched_es_title=None):
        if matched_es_title:
            return matched_es_title
        norm = query.lower()
        words = norm.split()
        for slang, target in ES_SEARCH_ALIASES.items():
            if re.search(rf"\b{re.escape(slang)}\b", norm):
                return target
        meaningful = [w for w in words if w not in QUERY_STOPWORDS and not w.isdigit()]
        if meaningful:
            return " ".join(meaningful)
        return query

    def is_metin2_query(self, norm_query, words, session):
        # 1. Contiene alguna palabra clave del juego
        if any(w in METIN2_TERMS for w in words):
            return True

        # 2. Contiene jerga de Metin2
        for slang_term in self.slang.keys():
            if re.search(rf"\b{re.escape(slang_term)}\b", norm_query):
                return True

        # 3. Coincidencia exacta en índice de búsqueda
        if norm_query in self.search_index:
            return True

        # 4. Objetos y términos comunes de Metin2 en español
        common_terms = [
            "luna llena", "hierro rojo", "espada envenenada", "acero negro",
            "diente de orco", "libro maldicion", "recuerdo demonio", "segador de la muerte",
            "beran setau", "dragon azul", "espada de ninfa", "espada de batalla",
            "partisana", "hoja electromagnetica", "zapatos fenix", "pendientes de ebano",
            "elixir del investigador", "espiral del tiempo", "cor draconis"
        ]
        if any(t in norm_query for t in common_terms):
            return True

        # 5. Memoria de sesión previa para seguimiento de mejoras/drops
        if session.get("last_entity") and (re.search(r"\+(\d)", norm_query) or any(w in words for w in ["donde", "cae", "pide", "yang", "mats", "subir"])):
            return True

        return False

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

        # 1. Saludos o cortesía breve (1 a 3 palabras)
        intent_name, conv_response = detect_conversational_intent(norm_query)
        if intent_name and len(words) <= 3:
            if self.llm.is_available():
                history = session.get("messages", [])
                llm_reply = self.llm.generate_response(user_query, history=history, is_metin2=True)
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

        # 2. Detección de tema: ¿Es sobre Metin2 o es una pregunta general externa?
        is_metin2 = self.is_metin2_query(norm_query, words, session)

        # ── CAMINO A: CONSULTA GENERAL (NO es de Metin2) ──────────────────
        # Responde 100% con Groq como asistente versátil de IA (estilo ChatGPT).
        # CERO llamadas a la wiki oficial de Gameforge, CERO búsquedas en catálogo alemán.
        if not is_metin2:
            if self.llm.is_available():
                history = session.get("messages", [])
                llm_reply = self.llm.generate_response(user_query, history=history, is_metin2=False)
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
                "message": "Hola, soy el Metin2 Oracle. Puedes preguntarme sobre cualquier tema general o consultar objetos, misiones y guías de Metin2."
            }

        # ── CAMINO B: CONSULTA DE METIN2 ──────────────────────────────────
        # Detectar si se pregunta por una mejora específica (+0 a +9) o materiales
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

        # Buscar si hay una entidad específica en catálogo o jerga
        matched_de_title = None

        # Búsqueda directa por frase exacta
        if norm_query in self.search_index:
            matched_de_title = self.search_index[norm_query]
        else:
            # Buscar coincidencia exacta de jerga conocida (ordenada de mayor a menor longitud)
            sorted_slang = sorted(self.slang.items(), key=lambda x: len(x[0]), reverse=True)
            for slang_term, de_title in sorted_slang:
                if re.search(rf"\b{re.escape(slang_term)}\b", norm_query):
                    matched_de_title = de_title
                    break

        # Búsqueda en nombres oficiales en español si la consulta contiene el nombre
        if not matched_de_title:
            sorted_search = sorted([(k, v) for k, v in self.search_index.items() if len(k) > 4], key=lambda x: len(x[0]), reverse=True)
            for norm_name, de_title in sorted_search:
                if re.search(rf"\b{re.escape(norm_name)}\b", norm_query):
                    matched_de_title = de_title
                    break

        # Memoria de conversación: usar última entidad si la consulta es un pronombre o contexto ("y a +9?", "donde cae?")
        if not matched_de_title and session.get("last_entity"):
            if target_plus is not None or any(w in words for w in ["donde", "cae", "dropea", "subir", "pide", "mats", "yang", "coste", "nivel"]):
                matched_de_title = session["last_entity"]

        # Determinar si el usuario pide ficha técnica con datos de la wiki
        # (materiales, costes en Yang, tabla de mejoras, drops o consulta directa de un ítem)
        card_keywords = ["pide", "materiales", "mats", "coste", "yang", "stats", "atributos", "tabla", "ficha", "dropea", "donde cae", "quien lo tira", "donde se consigue", "recompensa", "requisitos"]
        is_technical_card_request = bool(
            target_plus is not None or
            any(w in words for w in card_keywords) or
            (matched_de_title and len(words) <= 3)
        )

        # ── OBTENER HECHOS OFICIALES EN ESPAÑOL DESDE ES-WIKI ─────────────
        # Para evitar cualquier alucinación en guías, jefes, mapas, drops y mecánicas
        title_es_hint = None
        if matched_de_title:
            ent_info = self.catalog.get(matched_de_title, {})
            title_es_hint = ent_info.get("title_es") or self.de_to_es.get(matched_de_title)
        es_search_term = self.extract_es_search_term(user_query, matched_es_title=title_es_hint)
        es_grounding = fetch_es_wiki_grounding(es_search_term) if es_search_term else None

        # Si NO pide ficha técnica de un objeto específico (ej: jefes, mecánicas, guías, lore, zonas):
        # Responder de forma conversacional con Groq pero FUNDAMENTADO en los datos reales de es-wiki
        if not is_technical_card_request or not matched_de_title:
            if self.llm.is_available():
                history = session.get("messages", [])
                grounding_context = None
                if es_grounding:
                    grounding_context = (
                        f"[DATOS OFICIALES DE ES-WIKI DE METIN2 ({es_grounding['title']})]:\n"
                        f"{es_grounding['facts']}\n"
                        f"Fuente: {es_grounding['url']}\n\n"
                        f"IMPORTANTE: Basa tu respuesta en estos datos oficiales para no alucinar ubicaciones, drops ni requisitos."
                    )
                llm_reply = self.llm.generate_response(user_query, history=history, wiki_context=grounding_context, is_metin2=True)
                if llm_reply:
                    self._record_session_message(session_id, "user", user_query)
                    self._record_session_message(session_id, "assistant", llm_reply)
                    return {
                        "success": True,
                        "type": "conversational",
                        "message": llm_reply
                    }

        # Si aún no tenemos entidad pero hay LLM, responder con el LLM
        if not matched_de_title:
            if self.llm.is_available():
                history = session.get("messages", [])
                grounding_context = None
                if es_grounding:
                    grounding_context = f"[DATOS OFICIALES DE ES-WIKI ({es_grounding['title']})]:\n{es_grounding['facts']}"
                llm_reply = self.llm.generate_response(user_query, history=history, wiki_context=grounding_context, is_metin2=True)
                if llm_reply:
                    self._record_session_message(session_id, "user", user_query)
                    self._record_session_message(session_id, "assistant", llm_reply)
                    return {
                        "success": True,
                        "type": "conversational",
                        "message": llm_reply
                    }
            return {
                "success": False,
                "message": (
                    f"🤔 No encontré información específica sobre **\"{user_query}\"**.\n\n"
                    "Puedes preguntar cosas como:\n"
                    "- *\"qué pide para nueve la enve\"*\n"
                    "- *\"consejos para farmear yang a nivel 30\"*\n"
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

        # ── MODO HÍBRIDO: IA CONSEJOS + DATOS DE LA WIKI ──────────────────
        ai_message = None
        if self.llm.is_available():
            wiki_summary = ""
            if es_grounding:
                wiki_summary += f"[DATOS OFICIALES DE ES-WIKI ({es_grounding['title']})]:\n{es_grounding['facts']}\n\n"
            wiki_summary += f"[DATOS OFICIALES DE MEJORAS / EQUIPAMIENTO]:\nObjeto/Entidad: {title_es} ({matched_de_title}) - Categoría: {category_label}\n"
            if target_plus is not None:
                wiki_summary += f"Nivel consultado: +{target_plus}\n"
            if parsed_data.get("upgrades"):
                wiki_summary += "Datos de mejoras oficiales extraídos:\n"
                for up in parsed_data["upgrades"]:
                    lvl = up.get("level", "")
                    yang = up.get("yang", "")
                    mats = ", ".join([f"{m.get('count', 1)}x {m.get('display', '')}" for m in up.get("materials", [])])
                    attrs = ", ".join([f"{a.get('name', '')}: {a.get('value', '')}" for a in up.get("attributes", []) if a.get("value")])
                    wiki_summary += f"- Nivel {lvl}: Coste {yang} Yang | Materiales: {mats or 'Ninguno'} | Atributos: {attrs}\n"
            if parsed_data.get("drops_raw"):
                wiki_summary += f"Drops / Lugares de obtención: {parsed_data['drops_raw']}\n"
            if parsed_data.get("drops_text"):
                wiki_summary += f"Drops: {parsed_data['drops_text']}\n"
            if parsed_data.get("rewards_text"):
                wiki_summary += f"Recompensas oficiales: {parsed_data['rewards_text']}\n"

            history = session.get("messages", [])
            ai_message = self.llm.generate_response(user_query, history=history, wiki_context=wiki_summary, is_metin2=True)
            if ai_message:
                self._record_session_message(session_id, "user", user_query)
                self._record_session_message(session_id, "assistant", ai_message)

        # Si tenemos tarjeta parseada, devolver respuesta híbrida
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

        # Si falló la wiki pero la IA generó respuesta conversacional con consejos
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

