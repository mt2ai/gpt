# Metin2 Wiki Oracle (GPT)

Un asistente web ultraligero, de costo cero y sin alucinaciones para consultar información oficial y actualizada de **Metin2** en tiempo real. 

Conéctate desde tu móvil o PC mientras juegas, escribe consultas con errores ortográficos o jerga gamer (ej: *"q pide pa nuebe la espad bambu"*, *"donde cae el vms"* o *"mision biolo 30 dientes"*) y obtén respuestas exactas con las tablas oficiales del juego e iconos reales.

---

## Características

- **Cero Alucinaciones:** Extrae directamente las plantillas maestras (`Waffe/Layout`, `Rüstung/Layout`, `Quest/Layout`, `Monster/Layout`) de la wiki oficial alemana (la más actualizada y completa).
- **Tolerancia Extrema a Faltas y Jerga:** Mapea abreviaciones como *VMS, RIB, Biolo, Ebes, Enve, Dopes* y corrige errores tipográficos automáticamente.
- **Iconos Oficiales en Vivo:** Cada material de mejora, drop o recompensa de misión se muestra con su icono extraído de los servidores oficiales de Gameforge.
- **Mobile First & Ultra-Minimalista:** Diseñado para abrirse en el navegador de tu celular conectado a tu red Wi-Fi o desplegado en la nube.
- **Arquitectura de Costo $0:** No requiere APIs de pago (OpenAI, Anthropic). Corre en cualquier hardware modesto.

---

## Estructura del Proyecto

```text
├── data/
│   ├── catalog_index.json      # Catálogo de 3.421 entidades (Alemán <-> Español)
│   └── slang_dictionary.json   # Diccionario de jerga comunitaria de Metin2
├── core/
│   ├── wiki_client.py          # Cliente HTTP con caché para la API de MediaWiki
│   ├── parser_layouts.py       # Extractores deterministas de plantillas
│   └── engine.py               # Orquestador y limpiador de consultas
├── web/
│   ├── index.html              # Interfaz web estilo ChatGPT Mobile
│   ├── style.css               # Tema oscuro minimalista y responsive
│   └── app.js                  # Lógica del cliente y renderizado dinámico
├── scripts/
│   └── update_catalog.py       # Script de actualización periódica del catálogo
├── app.py                      # Servidor FastAPI
└── requirements.txt            # Dependencias mínimas
```

---

## Cómo Ejecutar en Local

1. Clona el repositorio:
   ```bash
   git clone https://github.com/mt2ai/gpt.git
   cd gpt
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Inicia el servidor:
   ```bash
   python app.py
   ```

4. Abre en tu navegador de la PC:
   `http://localhost:8000`

5. **Para conectarte desde tu celular en la misma red Wi-Fi:**
   - Averigua la IP local de tu PC (en Windows abre PowerShell y escribe `ipconfig`, ej: `192.168.1.50`).
   - Abre en el navegador de tu teléfono: `http://192.168.1.50:8000`

---

## Despliegue Gratuito en la Nube (24/7)

Puedes desplegar este repositorio de forma 100% gratuita en:
- **Hugging Face Spaces:** Crea un nuevo Space de tipo *Docker* o *Static/Python*.
- **Render.com / Railway:** Conecta este repo de GitHub, selecciona Python y comando de inicio `python app.py`.

---

## Licencia y Créditos

Este proyecto es para uso educativo y comunitario personal. El contenido y los iconos pertenecen a [Gameforge 4D GmbH](https://gameforge.com) y la comunidad de [Metin2 Wiki](https://de-wiki.metin2.gameforge.com/).
