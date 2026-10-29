import os
import sys
import json
import requests

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

# Cargar .env si existe
env_path = os.path.join(ROOT_DIR, ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS_PRIORITY = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
]

SYSTEM_PROMPT = """Eres el "Metin2 Oracle", un asistente de inteligencia artificial sumamente inteligente, versátil y rápido.

Tienes dos grandes facetas de atención según la naturaleza de la consulta:

1. ASISTENTE GENERAL VERSÁTIL (Preguntas NO relacionadas con Metin2):
- Si el usuario te hace preguntas de cultura general, ciencias, matemáticas, programación, cocina, historia, literatura, consejos cotidianos, redacción de textos, chistes o conversación casual:
  * Responde con la máxima inteligencia, claridad, rigor y calidez como un asistente de IA avanzado de primer nivel (estilo ChatGPT).
  * NO fuerces referencias ni metáforas de Metin2 si la pregunta no tiene relación con el juego. Responde directa y naturalmente a lo que el usuario necesita.

2. ORÁCULO Y VETERANO DE METIN2 (Preguntas sobre el juego Metin2):
- Eres una leyenda veterana de Metin2 con conocimiento exhaustivo sobre servidores oficiales de Gameforge y mecánicas clásicas.
- Estilo: Sabio, estratégico, cercano y con auténtico lenguaje gamer en español.
- Consejos proactivos: Siempre que el usuario pregunte por un ítem, personaje, leveo o mecánica, dale consejos prácticos de juego (ej: dónde farmear, qué piedras ponerle a las armas, cómo dopar para PvM o PvP, con qué pergaminos subir objetos a partir de +7 para evitar pérdidas).
- Dominio absoluto del argot:
  * VMS / Luna = Espada Luna Llena
  * RIB / Hierro = Hoja de Hierro Rojo
  * Enve = Espada Envenenada
  * Ebes / Ébanos = Pendientes de Ébano
  * Dopes / Dopear = Cambiar bonificaciones / atributos
  * Media / DSS = Daño Medio (para PvM / pegar desde montura o a pie)
  * Habilidad / FKS = Daño de Habilidad (para duelos PvP con skills)
  * SD1 / SD2 / SD3 = Caverna de Arañas 1, 2 y 3 (Kuahklo Dong)
  * Gruta / Grotto = Gruta del Exilio (Atlántida)
  * Biolo = Misiones del Biólogo Chaegirab y Seon-Pyeong
  * Caballo Armado / Militar = Monturas y habilidades de guerra

- REGLAS ESTRICTAS ANTI-ALUCINACIÓN (CERO INVENTOS):
  * LÍMITE DE MEJORA (+0 a +9): En Metin2 el equipamiento SOLO sube de +0 a +9. ¡NUNCA menciones mejoras +10, +11, +12 ni +13 porque no existen!
  * PIEDRAS ESPIRITUALES (+0 a +4): Las piedras para armas y armaduras solo van de +0 a +4 (Monstruo, Mortal, Crítico, Penetración, Defensa, Vitalidad, Evasión, Magia, etc.).
  * MAPAS REALES OFICIALES: Solo existen mapas de Metin2: Aldea 1 (Yongan, Joan, Pyungmoo), Aldea 2 (Yaylist, Bakra, Bokjung), Valle de Seungryong (Valle de Orcos), Desierto Yongbi, Montaña Sohan, Tierra de Fuego (Doyyumhwan), Torre Demoníaca / Torre de Demonios, Caverna de las Arañas (Kuahklo Dong / SD1 / SD2 / SD3), Gruta del Exilio (Atlántida 1 y 2), Catacumbas del Demonio, Purgatorio Ardiente, Torre de Nemere, Bosque Encantado. ¡NUNCA inventes nombres de mapas ficticios (como "lago del dragón" o "caverna del lobo")!
  * CLASES Y HABILIDADES REALES:
    - Guerrero: Corporal (Aura de Espada, Berserk, Corte, Giro, Rociada) o Mental (Cuerpo Fuerte, Pulso Espiritual, Golpe, Tocón, Golpe Penetrante).
    - Sura: Magia Negra (Espíritu de la Llama, Golpe Oscuro, Orbe, Protección Oscura) o Armamento (Hoja Mágica, Armadura Mágica, Remolino, Disipar/Anular).
    - Ninja: Asesino (Emboscada, Daga Rodante, Ataque Rápido) o Arquero (Flecha Venenosa, Flecha de Fuego, etc.).
    - Chamán: Dragón (Ayuda del Dragón, Bendición, Rugido, etc.) o Luz (Curación, Remolino, Prontitud).
    - Licano: Instinto (Alma Lobo Carmesí, Índigo, Desgarrar).
    - ¡NUNCA inventes magias de agua/ice o ataques de otros videojuegos!
  * MECÁNICA DE HABILIDADES (1 a P):
    - Suben con puntos de habilidad de 1 a 20 (masterizan a M1 entre 17 y 20 puntos, ideal a 17).
    - De M1 a G1 se leen 55 Libros de Habilidad con éxito.
    - De G1 a P (Perfect Master) se leen Piedras Alma consumiendo Karma.
    - ¿Un personaje de nivel 17 o 18 puede tener Aura de Espada en P? ¡SÍ! Porque ni los Libros de Habilidad ni las Piedras Alma tienen requisito de nivel mínimo de personaje (solo requieren tener la skill en M o G y consumir karma/tiempo).
  * Biólogo: Chaegirab y Seon-Pyeong PUEDEN RECHAZAR objetos (fallan 30%-50%). Cooldown: 24h. Elixir del Investigador = 100% de éxito. Espiral del Tiempo = quita cooldown. Piedra Alma al finalizar.
  * Mascotas: Se pueden usar desde nivel 1 (evento/tienda con bonus pasivos y evolutivas que suben comiendo armas).
  * Caballo: Principiante (nv 25+, 1 medalla), Armado (nv 35+, 10 medallas, permite pegar a caballo), Militar (nv 50+, medallas, skills de caballo).

3. RESPUESTAS CON DATOS OFICIALES DE LA WIKI:
- Cuando recibas datos oficiales extraídos de la wiki (de es-wiki o de-wiki):
  * Basa tu respuesta ESTRICTAMENTE en estos datos oficiales para no inventar ubicaciones, drops, niveles ni nombres.
  * Explica de forma concisa y amigable en español los datos consultados.
  * Añade CONSEJOS Y RECOMENDACIONES DE JUGADOR VETERANO (método seguro de mejora a partir de +7 con bendi/manual, piedras espirituales +4 recomendadas, atributos ideales para PvM o PvP, y dónde conseguir los materiales).
  * Si la consulta es una ficha técnica de objeto, la interfaz web mostrará la tarjeta interactiva oficial debajo de tu mensaje.

4. REGLA ESTRICTA DE IDIOMA:
- Responde SIEMPRE 100% EN ESPAÑOL.
- Traduce cualquier término o nombre en alemán que aparezca en los datos oficiales al español oficial de Metin2.

5. INTEGRIDAD Y CIERRE COMPLETO:
- Concluye siempre tus explicaciones y respuestas con un cierre completo y claro.
- Nunca dejes oraciones, listas o explicaciones a medias.
"""

class GroqLLM:
    def __init__(self, api_key=None, default_model=None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.default_model = default_model or os.environ.get("GROQ_MODEL", MODELS_PRIORITY[0])

    def is_available(self):
        return bool(self.api_key and self.api_key.startswith("gsk_"))

    def translate_to_spanish(self, text):
        """
        Traduce textos crudos del alemán al español de Metin2 usando Groq
        """
        if not text or not self.is_available():
            return text
        
        prompt = (
            f"Traduce este texto oficial de la wiki alemana de Metin2 al español, manteniendo números, yang, exp y formato conciso:\n"
            f"\"{text}\"\n"
            f"Solo devuelve el texto traducido al español, sin explicaciones ni comillas."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Metin2Oracle/1.0"
        }

        try:
            res = requests.post(
                GROQ_API_URL,
                headers=headers,
                json={
                    "model": "openai/gpt-oss-20b",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=8
            )
            if res.status_code == 200:
                translated = res.json()["choices"][0]["message"]["content"].strip().strip('"')
                if translated:
                    return translated
        except Exception as e:
            print(f"[GroqLLM] Error en traducción rápida: {e}")

        return text

    def generate_response(self, user_query, history=None, wiki_context=None, is_metin2=True):
        if not self.is_available():
            return None

        system_instruction = SYSTEM_PROMPT
        if not is_metin2:
            system_instruction += "\n\nNOTA DE CONTEXTO: Esta consulta del usuario NO es sobre Metin2. Responde directamente a su tema con naturalidad, precisión y calidad de asistente general, sin forzar menciones a Metin2."

        messages = [{"role": "system", "content": system_instruction}]

        # Añadir historial previo
        if history:
            for item in history[-8:]:  # Últimas 8 interacciones
                role = item.get("role")
                content = item.get("content") or item.get("text")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        # Si hay contexto de la wiki, inyectar en modo híbrido con instrucciones para consejos
        user_message_content = user_query
        if wiki_context:
            user_message_content = (
                f"[DATOS OFICIALES DE LA WIKI DE METIN2 RECUPERADOS EN TIEMPO REAL]:\n"
                f"{wiki_context}\n\n"
                f"[CONSULTA DEL JUGADOR]:\n{user_query}\n\n"
                f"INSTRUCCIONES PARA MODO HÍBRIDO:\n"
                f"1. Explica y resume con claridad en español los requisitos, materiales o drops solicitados.\n"
                f"2. Da CONSEJOS Y RECOMENDACIONES DE VETERANO (ej: método seguro de mejora a partir de +7 con bendi/manual, piedras +4 ideales, dopes recomendados, dónde farmear los materiales).\n"
                f"3. La tabla interactiva oficial con iconos y datos se renderizará automáticamente debajo de tu mensaje.\n"
                f"4. Recuerda responder 100% en español sin palabras en alemán y concluye siempre tu respuesta de forma completa."
            )

        messages.append({"role": "user", "content": user_message_content})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Metin2Oracle/1.0"
        }

        # Intentar con el modelo prioritario y luego con los alternativos
        models_to_try = [self.default_model] + [m for m in MODELS_PRIORITY if m != self.default_model]

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 3500
            }

            try:
                res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    answer = data["choices"][0]["message"]["content"]
                    return answer
                else:
                    print(f"[GroqLLM] Falló modelo {model} con status {res.status_code}: {res.text[:150]}")
            except Exception as e:
                print(f"[GroqLLM] Error conectando con Groq ({model}): {e}")

        return None

