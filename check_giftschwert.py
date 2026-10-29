import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

API_URL = "https://de-wiki.metin2.gameforge.com/api.php"
HEADERS = {"User-Agent": "Metin2Assistant/1.0 (contact@example.com)"}

def check_giftschwert():
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "titles": "Giftschwert",
        "format": "json"
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        page = list(data["query"]["pages"].values())[0]
        content = page["revisions"][0]["*"]
        
    print("LINEAS DE UPGRADE EN GIFTSCHWERT:")
    for line in content.split("\n"):
        if any(k in line for k in ["Upgradeitem", "Material", "Kosten", "Vorlage:", "SWaffen"]):
            print(line)

if __name__ == "__main__":
    check_giftschwert()
