import urllib.request
import urllib.parse
import json
import time
import re

DE_API_URL = "https://de-wiki.metin2.gameforge.com/api.php"
ES_API_URL = "https://es-wiki.metin2.gameforge.com/api.php"
HEADERS = {"User-Agent": "Metin2GPT/1.0 (Public OpenSource Assistant; contact@mt2ai.org)"}

# Caché en memoria para no repetir consultas en la misma sesión
_PAGE_CACHE = {}
_IMAGE_CACHE = {}
_ES_PAGE_CACHE = {}
_ES_SEARCH_CACHE = {}

def fetch_wiki_api(params, base_url=DE_API_URL):
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[WikiClient] Error al consultar API ({base_url}) ({params.get('titles') or params.get('srsearch')}): {e}")
        return None

def get_page_content(title_de):
    """
    Descarga el contenido oficial en wikitext de una página alemana
    Sigue redirecciones automáticamente
    """
    if title_de in _PAGE_CACHE:
        return _PAGE_CACHE[title_de]
        
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": title_de,
        "redirects": "1",
        "format": "json"
    }
    data = fetch_wiki_api(params, base_url=DE_API_URL)
    if not data:
        return ""
        
    pages = data.get("query", {}).get("pages", {})
    for _, page in pages.items():
        revisions = page.get("revisions", [])
        if revisions:
            content = revisions[0].get("*", "")
            _PAGE_CACHE[title_de] = content
            return content
    return ""

def get_image_url(image_name):
    """
    Obtiene la URL directa oficial de un icono o imagen
    """
    if not image_name.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
        image_name = f"{image_name}.png"
        
    if image_name in _IMAGE_CACHE:
        return _IMAGE_CACHE[image_name]
        
    params = {
        "action": "query",
        "titles": f"Datei:{image_name}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    data = fetch_wiki_api(params, base_url=DE_API_URL)
    if data:
        pages = data.get("query", {}).get("pages", {})
        for _, p in pages.items():
            info = p.get("imageinfo", [])
            if info:
                url = info[0].get("url")
                _IMAGE_CACHE[image_name] = url
                return url
                
    return None

# ── INTEGRACIÓN ES-WIKI (https://es-wiki.metin2.gameforge.com/) ────────────

def clean_es_wikitext(text, max_lines=45):
    """
    Convierte el wikitext crudo de es-wiki en texto estructurado en español,
    eliminando sintaxis wiki, enlaces interidiomas y extrayendo campos clave.
    """
    if not text:
        return ""
    # Remover comentarios
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # Remover enlaces de idiomas (ej: [[de:Flammenkönig]], [[en:...]], etc.)
    text = re.sub(r'\[\[[a-z]{2}:[^\]]+\]\]', '', text)
    text = re.sub(r'\b[a-z]{2}:[^\n]+', '', text)
    # Reemplazar plantillas comunes como {{To|Nombre}} por Nombre
    text = re.sub(r'\{\{To\|([^}]+)\}\}', r'\1', text)
    # Reemplazar enlaces wiki [[Enlace|Texto]] por Texto o [[Texto]] por Texto
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', text)
    # Remover etiquetas HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    extracted = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('{|', '|}', '|--', '|-', '{{', '}}')):
            continue
        if line.startswith('|'):
            line = line.lstrip('|').strip()
            if '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().replace('*', ' ').strip()
                if k.lower() in ['imagen', 'image', 'diseño', 'icono', 'icon', 'width', 'align', 'color']:
                    continue
                if v:
                    extracted.append(f"{k}: {v}")
                continue
        if line and not line.startswith('!'):
            extracted.append(line)
            
    return '\n'.join(extracted[:max_lines])

def search_es_wiki(query, limit=2):
    """
    Busca artículos relevantes en la wiki oficial en español de Metin2
    """
    norm = query.strip()
    if not norm:
        return []
    if norm in _ES_SEARCH_CACHE:
        return _ES_SEARCH_CACHE[norm]
        
    params = {
        "action": "query",
        "list": "search",
        "srsearch": norm,
        "format": "json",
        "srlimit": limit
    }
    data = fetch_wiki_api(params, base_url=ES_API_URL)
    if not data:
        return []
        
    results = data.get("query", {}).get("search", [])
    titles = [r["title"] for r in results if r.get("title")]
    _ES_SEARCH_CACHE[norm] = titles
    return titles

def get_es_page_content(title):
    """
    Descarga el contenido oficial de una página de es-wiki
    """
    if title in _ES_PAGE_CACHE:
        return _ES_PAGE_CACHE[title]
        
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": title,
        "redirects": "1",
        "format": "json"
    }
    data = fetch_wiki_api(params, base_url=ES_API_URL)
    if not data:
        return ""
        
    pages = data.get("query", {}).get("pages", {})
    for _, page in pages.items():
        if _ != "-1":
            revisions = page.get("revisions", [])
            if revisions:
                content = revisions[0].get("*", "")
                _ES_PAGE_CACHE[title] = content
                return content
    return ""

def fetch_es_wiki_grounding(search_term):
    """
    Busca en es-wiki y devuelve un bloque de hechos oficiales limpios en español.
    """
    if not search_term or len(search_term.strip()) < 2:
        return None
        
    titles = search_es_wiki(search_term, limit=1)
    if not titles:
        return None
        
    best_title = titles[0]
    raw_content = get_es_page_content(best_title)
    if not raw_content:
        return None
        
    cleaned = clean_es_wikitext(raw_content)
    if not cleaned or len(cleaned.strip()) < 20:
        return None
        
    return {
        "title": best_title,
        "url": f"https://es-wiki.metin2.gameforge.com/index.php/{urllib.parse.quote(best_title)}",
        "facts": cleaned
    }
