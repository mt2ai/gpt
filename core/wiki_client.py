import urllib.request
import urllib.parse
import json
import time

API_URL = "https://de-wiki.metin2.gameforge.com/api.php"
HEADERS = {"User-Agent": "Metin2GPT/1.0 (Public OpenSource Assistant; contact@mt2ai.org)"}

# Caché en memoria para no repetir consultas en la misma sesión
_PAGE_CACHE = {}
_IMAGE_CACHE = {}

def fetch_wiki_api(params):
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[WikiClient] Error al consultar API ({params.get('titles') or params.get('search')}): {e}")
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
    data = fetch_wiki_api(params)
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
    data = fetch_wiki_api(params)
    if data:
        pages = data.get("query", {}).get("pages", {})
        for _, p in pages.items():
            info = p.get("imageinfo", [])
            if info:
                url = info[0].get("url")
                _IMAGE_CACHE[image_name] = url
                return url
                
    return None
