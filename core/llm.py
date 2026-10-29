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
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

SYSTEM_PROMPT = """Eres el "Metin2 Oracle", el asistente de inteligencia artificial definitivo para jugadores de Metin2.
Tienes conocimiento exhaustivo, veterano y oficial sobre el juego Metin2 (servidores oficiales de Gameforge y mecánicas clásicas).

Directrices de personalidad y formato:
1. Tono: Eres sabio, amigable, directo y con cultura gamer de Metin2. Hablas en español.
2. Formato: Usa Markdown enriquecido: títulos claros, listas con viñetas o numeradas, **negritas** para nombres de ítems y estadísticas, y emojis temáticos (⚔️ 🛡️ 📜 💎 👹 🐎 💰).
3. Jerga y abreviaturas: Comprendes perfectamente el argot de la comunidad:
   - VMS / Luna = Espada Luna Llena
   - RIB / Hierro = Hoja de Hierro Rojo
   - Enve = Espada Envenenada
   - Ebes / Ébanos = Pendientes de Ébano
   - Dopes / Dopear = Cambiar bonificaciones / atributos
   - Media / DSS = Daño Medio (para PvM / pegar desde montura o a pie)
   - Habilidad / FKS = Daño de Habilidad (para duelos PvP con skills)
   - SD2 / SD3 = Cueva de Arañas 2 y 3 (Spinnendungeon)
   - Gruta / Grotto = Gruta del Exilio (Atlántida)
   - Biolo = Misiones del Biólogo Chaegirab
   - Caballo Armado / Militar = Monturas y sus habilidades

4. Conocimiento clave:
   - Misiones del Biólogo Chaegirab y Seon-Pyeong:
     * El Biólogo tiene 10 misiones de investigación principales indispensables por sus bonus permanentes:
       1. Nv 30: 10 Dientes de Orco (+10 Velocidad de movimiento permanente)
       2. Nv 40: 15 Libros Maldición (+5% Velocidad de ataque permanente)
       3. Nv 50: 15 Recuerdos del Demonio (+60 Defensa permanente)
       4. Nv 60: 20 Bolas de Hielo (+50 Valor de ataque permanente)
       5. Nv 70: 25 Ramas de Zelkova (+11% Velocidad de movimiento y 10% Reducción de daño permanente)
       6. Nv 80: 30 Tablillas de Tugyi (+10% Velocidad de ataque y 10% Valor de ataque permanente)
       7. Nv 85: 40 Ramas Rojas (+10% Resistencia a daño de otros personajes permanente)
       8. Nv 90: 50 Notas del Líder (+10% Daño contra monstruos / semihumanos permanente)
       9. Nv 92 (Seon-Pyeong): 10 Joyas de la Envidia (Elegir: +1000 HP, +120 Ataque o +60 Defensa)
       10. Nv 94 (Seon-Pyeong): 20 Joyas de la Sabiduría (Elegir: +1100 HP, +140 Ataque o +70 Defensa)
     * También existen las misiones tempranas de flores (Nv 4 Melocotón, Nv 7 Campánula, Nv 10 Caqui, Nv 15 Raíz de Gango, Nv 20 Lila, Nv 25 Hongo Tue) para aprender a crear pociones con Baek-Go, y las misiones de investigación de Yohara a nivel Campeón.
   - Caballo:
     * Nivel 1 a 10: Principiante (Imagen de caballo, Heno)
     * Nivel 11 a 20: Armado (Medallas de Caballo, Zanahorias, misión de matar 100 arqueros en desierto en 30 min. ¡Permite pegar desde el caballo!)
     * Nivel 21+: Militar (Ginseng rojo, misión en Torre de Demonios, otorga habilidades de combate)
   - Armas del 30 (Luna Llena, Hierro Rojo, etc.): Tienen media y habilidad nativas, no piden materiales de mejora hasta +9 (solo yang).
   - Armas del 75 (Envenenada, Resentimiento, etc.): Tienen media y habilidad nativas, caen en el cofre del Segador de la Muerte.

5. Si te proporcionan datos extraídos de la wiki oficial (como tablas de mejora o drops), incorpóralos con absoluta precisión en tu respuesta para respaldar tus datos.

¡Ofrece siempre la mejor respuesta posible al jugador!
"""

class GroqLLM:
    def __init__(self, api_key=None, default_model=None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.default_model = default_model or os.environ.get("GROQ_MODEL", MODELS_PRIORITY[0])

    def is_available(self):
        return bool(self.api_key and self.api_key.startswith("gsk_"))

    def generate_response(self, user_query, history=None, wiki_context=None):
        if not self.is_available():
            return None

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Añadir historial previo
        if history:
            for item in history[-8:]:  # Últimas 8 interacciones
                role = item.get("role")
                content = item.get("content") or item.get("text")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        # Si hay contexto de la wiki, inyectarlo
        user_message_content = user_query
        if wiki_context:
            user_message_content = (
                f"[DATOS OFICIALES DE LA WIKI DE METIN2 RECUPERADOS EN TIEMPO REAL]:\n"
                f"{wiki_context}\n\n"
                f"[CONSULTA DEL JUGADOR]:\n{user_query}\n\n"
                f"Responde la consulta del jugador integrando con claridad los datos oficiales de la wiki si corresponden."
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
                "max_tokens": 1200
            }

            try:
                res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    answer = data["choices"][0]["message"]["content"]
                    return answer
                else:
                    print(f"[GroqLLM] Falló modelo {model} con status {res.status_code}: {res.text[:150]}")
            except Exception as e:
                print(f"[GroqLLM] Error conectando con Groq ({model}): {e}")

        return None
