import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

API_URL = "https://de-wiki.metin2.gameforge.com/api.php"
HEADERS = {"User-Agent": "Metin2Assistant/1.0 (contact@example.com)"}

def check_images():
    # Consultar cómo se llaman las imágenes de Perla Blanca, Dämonenandenken, etc.
    items = ["Weiße Perle", "Dämonenandenken", "Dämonenedelstein", "Unbekannter Talisman+"]
    for it in items:
        params = {
            "action": "query",
            "titles": f"Datei:{it}.png|Datei:{it}.jpg",
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json"
        }
        url = f"{API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            pages = data.get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if int(pid) > 0:
                    print(f"ENCONTRADA: {p.get('title')} -> {p.get('imageinfo', [{}])[0].get('url')}")
                else:
                    print(f"NO EXISTE: {p.get('title')}")

if __name__ == "__main__":
    check_images()
