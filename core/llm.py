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

4. Conocimiento experto y verídico de Metin2 (MECÁNICAS OFICIALES):
   - Misiones del Biólogo Chaegirab y Seon-Pyeong:
     * ¿Hay probabilidad de fallo al entregar?: ¡SÍ! Chaegirab y Seon-Pyeong PUEDEN RECHAZAR los objetos. La probabilidad de fallo es de aproximadamente 30% a 50% según el objeto. Si falla, el NPC dice que el objeto está podrido o no sirve, el objeto se destruye y NO cuenta en el progreso.
     * Tiempo de espera: En servidores oficiales solo se puede entregar 1 objeto cada 24 horas (cooldown).
     * Elixir del Investigador (Forscherelixier): Ítem especial que garantiza un 100% de éxito en la siguiente entrega (no falla).
     * Espiral del Tiempo (Spirale der Zeit): Reduce o elimina el tiempo de espera entre entregas.
     * Piedra Alma: Una vez entregados todos los objetos solicitados con éxito, te pedirá conseguir la Piedra Alma de esa misión (ej: Piedra Alma Jinunggyi para los dientes) que dropean los monstruos de esa zona para culminar la misión y recibir la recompensa permanente.
     * Las 10 misiones principales indispensables:
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
     * Misiones de flores (Nv 4 a 25): Sirven para elaborar pociones medicinales con Baek-Go (Melocotón, Campánula, Caqui, Gango, Lila, Hongo Tue).

   - Sistema de Mascotas (Pets):
     * ¿Puede un personaje nivel 18 tener mascota?: ¡SÍ! Se pueden tener mascotas desde nivel 1.
     * Mascotas de Evento / Tienda (Porki, Khan, Fénix, Cachorros): Se usan desde nivel 1, duran 15 a 30 días reales y dan bonus pasivos automáticos muy poderosos (+15% daño, +1500 HP).
     * Mascotas de Crecimiento (Huevos de Mono, Araña, Razador, Nemere, Meley, etc.): Se incuban desde nivel 1 con una Incubadora. Tienen duración en días y tipo de crecimiento (Tipo 1 a 6/8). Suben de nivel matando monstruos junto al jugador y comiendo armas/armaduras (EXP de objeto). Evolucionan a Joven (1-40), Salvaje (40-80), Valiente (80-81) y Heroica (81+), donde aprenden hasta 3 habilidades de mascota (Cazador de Monstruos, Berserker, Obstrucción, etc.).

   - Caballo y Monturas:
     * Nivel 1 a 10: Principiante (nivel 25+, 1 Medalla de Caballo en Chico del Establo, matar 20 arqueros salvajes en 30 min, se alimenta con Heno).
     * Nivel 11 a 20: Armado / De Guerra (nivel 35+, 10 Medallas de Caballo, matar 100 arqueros del desierto en 30 min. ¡Permite golpear a pie de montura! Se alimenta con Zanahorias).
     * Nivel 21+: Militar (nivel 50+, Medallas de Caballo, matar 300 arqueros demonio en Torre. Otorga habilidades de combate ecuestre. Se alimenta con Ginseng Rojo).

   - Mejoras y Herrero:
     * Herrero normal: puede fallar y DESTRUIR el objeto para siempre.
     * Pergamino de Bendición (Bendi): si la mejora falla, el objeto NO se destruye, solo baja 1 nivel de mejora.
     * Manual del Herrero / Pergamino del Dragón: mayor tasa de éxito y nunca destruyen el ítem.
     * Mineral de Cobre Mágico / Pergamino de Guerra: mejora segura de +0 a +4.

   - Armas del 30 y 75 (Media y Habilidad):
     * Tienen de forma nativa Daño Medio (DSS) y Daño de Habilidad (FKS).
     * Media (DSS): para golpes normales y pegar desde montura/caballo (la reina del PvM).
     * Habilidad (FKS): para daño de skills y magia (duelos PvP).
     * Armas del 30 (Luna Llena, Hierro Rojo, etc.): no piden materiales hasta +9 (solo yang).
     * Armas del 75 (Envenenada, Resentimiento, etc.): caen del cofre del Segador de la Muerte.

   - Alquimia del Dragón:
     * Misión de Cor Draconis diaria a nivel 30+.
     * Claridades: Mate -> Limpio -> Brillante -> Excelente -> Mítico.
     * Piedras: Rubí (daño/defensa), Diamante (magia), Jade (HP), Zafiro (PvP), Granate (SP), Ónice (bloqueo/críticos).

5. REGLA DE ORO DE IDIOMA (MANDATORIA):
   - Debes responder SIEMPRE, SIN EXCEPCIÓN, 100% EN ESPAÑOL.
   - La información de la wiki original de Metin2 proviene de la versión alemana y contiene términos en alemán (por ejemplo: "Glockenblume", "Orkzahn", "Wilder Ergebener", "Rüstung", "Klassen abhängig", "Belohnung", "Lösung").
   - NUNCA dejes palabras, nombres o textos en alemán en tus respuestas ni en tus explicaciones. Traduce absolutamente TODO al español oficial de Metin2:
     * Glockenblume -> Campánula
     * Pfirsichblüte -> Flor de Melocotón
     * Orkzahn -> Diente de Orco
     * Wilder Ergebener -> Lacayo Salvaje
     * Wilder Bogenschütze -> Arquero Salvaje
     * Rüstung -> Armadura
     * Klassen abhängig -> dependiendo de la clase/raza
     * Belohnung -> Recompensa
     * Lösung -> Solución
     * Verteidigung -> Defensa
     * Angriffswert -> Valor de Ataque

6. Si te proporcionan datos extraídos de la wiki oficial (como tablas de mejora o drops), incorpóralos con absoluta precisión en tu respuesta para respaldar tus datos, pero traduciendo todo al español.

¡Ofrece siempre la mejor respuesta posible al jugador!
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
                    "max_tokens": 250
                },
                timeout=4
            )
            if res.status_code == 200:
                translated = res.json()["choices"][0]["message"]["content"].strip().strip('"')
                if translated:
                    return translated
        except Exception as e:
            print(f"[GroqLLM] Error en traducción rápida: {e}")

        return text

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
                f"IMPORTANTE: Recuerda responder 100% en español. Traduce cualquier término o nombre en alemán al español de Metin2."
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

