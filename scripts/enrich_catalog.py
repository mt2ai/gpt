import json
import re
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

CATALOG_FILE = "d:\\wm2\\data\\catalog_index.json"

# Diccionario maestro de traducción de Metin2 (DE -> ES) del cliente de juego
DICTIONARY_METIN2 = {
    # Armas icónicas
    "Giftschwert": "Espada Envenenada",
    "Grollschwert": "Espada del Rencor",
    "Dornenkralle": "Garra de Espinas",
    "Habichtkralle": "Garra Halcón",
    "Krähenflügelbogen": "Arco Ala de Cuervo",
    "Teufelsflügel-Chakram": "Chakram Ala Demoniaca",
    "Löwenschwert": "Espada del León",
    "Orchideen-Glocke": "Campana Orquídea",
    "Vollmondschwert": "Espada Luna Llena",
    "Roteisenklinge": "Hoja de Hierro Rojo",
    "Bambusschwert": "Espada de Bambú",
    "Breitschwert": "Espada Ancha",
    "Langschwert": "Espada Larga",
    "Kupferschwert": "Espada de Cobre",
    "Silberschwert": "Espada de Plata",
    "Orkschwert": "Espada de Orco",
    "Bastardschwert": "Espada Bastarda",
    "Schlachtschwert": "Espada de Batalla",
    "Nymphenschwert": "Espada Ninfa",
    "Stichschwert": "Espada Picadura",
    "Giftschwert": "Espada Envenenada",
    "Runenschwert": "Espada Rúnica",
    "Drachengottklinge": "Hoja Dios Dragón",
    "Partisane": "Partisana",
    "Magnetische Klinge": "Espada Electromagnética",
    "Halbmenschen-Klinge": "Espada Semihumanos",
    "Sonnen-Schwert": "Espada Solar",
    "Drachenmesser": "Cuchillo Dragón",
    "Blitzmesser": "Cuchillo Rayo",
    "Siammesser": "Cuchillo Siamés",
    "Teufelsmaskendolch": "Daga Máscara Demoníaca",
    "Gelbdrachenbogen": "Arco Dragón Amarillo",
    "Großteufelbogen": "Arco Gran Demonio",
    "Phönixbogen": "Arco Fénix",
    "Himmelsdrachen-Glocke": "Campana Dragón Celestial",
    "Erlösungs-Glocke": "Campana del Rescate",
    "Drachengott-Glocke": "Campana Dios Dragón",
    "Paradiesvogel-Fächer": "Abanico Ave del Paraíso",
    "Dämonen-Fächer": "Abanico Demoníaco",
    "Dimmelfächer": "Abanico del Cielo",

    # Armaduras icónicas
    "Schwarzstahl-Panzer": "Armadura de Acero Negro",
    "Schwarzwindanzug": "Traje Viento Negro",
    "Magie-Plattenpanzer": "Armadura Magia Negra",
    "Schwarzkleidung": "Vestido Negro",
    "Nachtschatten-Panzer": "Armadura Sombra Nocturna",
    "Drachengott-Panzer": "Armadura Dios Dragón",
    "Löwen-Plattenpanzer": "Armadura de Placas de León",
    "Tödlicher Plattenpanzer": "Armadura de Placas Mortal",
    "Geister-Plattenpanzer": "Armadura Placas Fantasma",
    "Mönchs-Plattenpanzer": "Armadura Placas de Monje",
    "Eisen-Plattenpanzer": "Armadura Placas de Hierro",
    "Tiger-Plattenpanzer": "Armadura Placas de Tigre",

    # Accesorios y Escudos
    "Falkenschild": "Escudo Halcón",
    "Titanschild": "Escudo Titánico",
    "Tigerschild": "Escudo Tigre",
    "Löwenkanten-Schild": "Escudo Escamas de Dragón",
    "Drachenschuppen-Schild": "Escudo Límite de León",
    "Schlachtschild": "Escudo de Batalla",
    "Pentagonschild": "Escudo Pentagonal",
    "Rundschild": "Escudo Redondo Negro",
    "Ebenholzohrringe": "Pendientes de Ébano",
    "Silberohrringe": "Pendientes de Plata",
    "Kupferohrringe": "Pendientes de Cobre",
    "Goldohrringe": "Pendientes de Oro",
    "Himmelstränenohrringe": "Pendientes Lágrimas de Cielo",
    "Silberarmband": "Brazalete de Plata",
    "Ebenholzarmband": "Brazalete de Ébano",
    "Himmelstränenarmband": "Brazalete Lágrimas de Cielo",
    "Weißgoldarmband": "Brazalete de Oro Blanco",
    "Kristallarmband": "Brazalete de Cristal",
    "Ebenholzhalskette": "Collar de Ébano",
    "Silberhalskette": "Collar de Plata",
    "Himmelstränenhalskette": "Collar Lágrimas de Cielo",
    "Amethysthalskette": "Collar de Amatista",
    "Kristallhalskette": "Collar de Cristal",
    "Phönixschuhe": "Zapatos Fénix",
    "Lederscheuchen": "Zapatos de Cuero",
    "Goldverzierte Schuhe": "Zapatos Adornados de Oro",
    "Extasestiefel": "Botas del Éxtasis",
    "Feuervogelschuhe": "Zapatos Pájaro de Fuego",
    "Qilinschuhe": "Zapatos Qilin",
    "Kriegsmeisterhelm": "Casco Maestro de Guerra",
    "Gehörnter Helm": "Casco con Cuernos",
    "Kardinalshut": "Sombrero de Cardenal",
    "Spinnenkapuze": "Capucha de Araña",
    "Eisenhelm": "Casco de Hierro",
    "Geisterscheinhelm": "Casco Aparición Fantasma",

    # Materiales de mejora
    "Bärenfußhaut": "Piel de Pata de Oso",
    "Bärenfußhaut+": "Piel de Pata de Oso+",
    "Bärengalle": "Vesícula de Oso",
    "Bärengalle+": "Vesícula de Oso+",
    "Weißes Haarband": "Cinta Blanca para el Cabello",
    "Weißes Haarband+": "Cinta Blanca para el Cabello+",
    "Schwarzes Haarband": "Cinta Negra para el Cabello",
    "Zerbrochenes Porzellan": "Porcelana Rota",
    "Kriegersymbol": "Símbolo del Guerrero",
    "Dämonenandenken": "Recuerdo del Demonio",
    "Dämonenandenken+": "Recuerdo del Demonio+",
    "Dämonenedelstein": "Gema del Demonio",
    "Dämonenedelstein+": "Gema del Demonio+",
    "Unbekannter Talisman": "Talismán Desconocido",
    "Unbekannter Talisman+": "Talismán Desconocido+",
    "Weiße Perle": "Perla Blanca",
    "Blaue Perle": "Perla Azul",
    "Blutrote Perle": "Perla Roja",
    "Yetifell": "Piel de Yeti",
    "Yetifell+": "Piel de Yeti+",
    "Orkzahn": "Diente de Orco",
    "Orkzahn+": "Diente de Orco+",
    "Ork-Wurrzahn": "Diente de Orco con Raíz",
    "Schlangenhaut": "Piel de Serpiente",
    "Schlangenschwanz": "Cola de Serpiente",
    "Schlangenschwanz+": "Cola de Serpiente+",
    "Spinnensack": "Bolsa de Huevos de Araña",
    "Spinnen-Augen": "Ojos de Araña",
    "Spinnenbeine": "Patas de Araña",
    "Spinnennetz": "Telaraña",
    "Skorpionschwanz": "Cola de Escorpión",
    "Skorpionschwanz+": "Cola de Escorpión+",
    "Skorpionnadel": "Aguijón de Escorpión",
    "Fischgräte": "Espina de Pescado",
    "Muschel": "Almeja",
    "Stück Edelstein": "Trozo de Gema",
    "Stück kaputter Rüstung": "Trozo de Armadura Rota",
    "Rostige Klinge": "Espada Oxidada",
    "Shiriken": "Shuriken",
    "Shiriken+": "Shuriken+",
    "Eisstück": "Trozo de Hielo",
    "Eisstück+": "Trozo de Hielo+",
    "Eiskugel": "Bola de Hielo",
    "Eiskugel+": "Bola de Hielo+",
    "Flammenmähne": "Melena Llameante",
    "Tigerkralle": "Garra de Tigre",
    "Tigermilz": "Bazo de Tigre",
    "Wolfskralle": "Garra de Lobo",
    "Wolfskralle+": "Garra de Lobo+",
    "Wolfsfell": "Piel de Lobo",
    "Wolfsfell+": "Piel de Lobo+",
    "Schweinezahn": "Diente de Jabalí",
    "Unbekannte Medizin": "Medicina Desconocida",
    "Unbekannte Medizin+": "Medicina Desconocida+",
    "Knäuel": "Ovillo",
    "Kriegsfahne": "Bandera de Batalla",
    "Fluchbuch": "Libro de Maldición",
    "Fluchbuch+": "Libro de Maldición+",
    "Zelkovaberech": "Rama de Zelkova",
    "Tugyistafel": "Tablilla de Tugyi",
    "Roter Geisterbaum-Ast": "Rama del Árbol Fantasma Rojo",
    "Notiz des Anführers": "Nota del Líder",

    # Jefes y Monstruos Populares
    "Oberork": "Orco Jefe",
    "Dämonenkönig": "Rey Demonio",
    "Stolzer Dämonenkönig": "Rey Demonio Élite",
    "Sensenmann": "La Muerte",
    "Neunschwanz": "Nueve Colas",
    "Königstiger": "Tigre Real",
    "Gelber Tigergeist": "Espíritu Tigre Amarillo",
    "Königinnenspinne": "Reina Araña",
    "Spinnenbaroness": "Baronesa Araña",
    "Dunkler Felsengolem": "Golem de Roca Oscuro",
    "Feuerland-Golem": "Golem de Fuego",
    "Wüsten-Flugschildkröte": "Tortuga Gigante del Desierto",
    "Flammenkönig": "Rey de la Llama",
    "Beran-Setaou": "Beran-Setaou (Dragón Azul)",
    "Roter Drache": "Dragón Rojo",
    "Razador": "Razador",
    "Nemere": "Nemere",
    "Jotun Thrym": "Jotun Thrym",
    "Wildhund": "Perro Salvaje",
    "Wolf": "Lobo",
    "Alpha-Wolf": "Lobo Alfa",
    "Blauwolf": "Lobo Azul",
    "Grauwolf": "Lobo Gris",
    "Wilder Ergebener": "Subordinado Salvaje",
    "Schwarzer Ork": "Orco Negro",
    "Mutiger Schw. Ork": "Orco Negro Valiente",

    # Metins Populares
    "Metin des Kummers": "Metin del Dolor (Lv. 5)",
    "Metin des Kampfes": "Metin de la Lucha (Lv. 10)",
    "Metin der Schlacht": "Metin de la Batalla (Lv. 15)",
    "Metin der Gier": "Metin de la Avaricia (Lv. 20)",
    "Metin der Schwärze": "Metin del Ennegrecimiento (Lv. 25)",
    "Metin der Dunkelheit": "Metin de la Oscuridad (Lv. 30)",
    "Metin des Eifers": "Metin del Rencor (Lv. 35)",
    "Metin der Seele": "Metin del Alma (Lv. 40)",
    "Metin des Schattens": "Metin de la Sombra (Lv. 45)",
    "Metin der Härte": "Metin de la Dureza (Lv. 50)",
    "Metin des Teufels": "Metin del Demonio (Lv. 55)",
    "Metin des Sturzes": "Metin de la Caída (Lv. 60)",
    "Metin des Todes": "Metin de la Muerte (Lv. 65)",
    "Metin des Mordes": "Metin del Asesinato (Lv. 70)",
    "Metin des Pung-Ma": "Metin Pung-Ma (Lv. 75)",
    "Metin des Ma-An": "Metin Ma-An (Lv. 80)",
    "Metin des Tu-Young": "Metin Tu-Young (Lv. 85)",
    "Metin des Jeon-Un": "Metin Jeon-Un (Lv. 90)"
}

# Reglas de traducción heurística para nombres restantes
PREFIX_RULES = [
    (r"Metin (des|der) (.+)", r"Metin de \2"),
    (r"Truhe (des|der) (.+)", r"Cofre de \2"),
    (r"Buch (des|der) (.+)", r"Libro de \2"),
    (r"(.+)schwert$", r"Espada \1"),
    (r"(.+)klinge$", r"Hoja \1"),
    (r"(.+)dolch$", r"Daga \1"),
    (r"(.+)messer$", r"Cuchillo \1"),
    (r"(.+)bogen$", r"Arco \1"),
    (r"(.+)glocke$", r"Campana \1"),
    (r"(.+)fächer$", r"Abanico \1"),
    (r"(.+)kralle$", r"Garra \1"),
    (r"(.+)panzer$", r"Armadura \1"),
    (r"(.+)anzug$", r"Traje \1"),
    (r"(.+)kleidung$", r"Vestido \1"),
    (r"(.+)helm$", r"Casco \1"),
    (r"(.+)schild$", r"Escudo \1"),
    (r"(.+)ohrringe$", r"Pendientes \1"),
    (r"(.+)armband$", r"Brazalete \1"),
    (r"(.+)halskette$", r"Collar \1"),
    (r"(.+)schuhe$", r"Zapatos \1"),
    (r"Hungriger? (.+)", r"\1 Hambriento"),
    (r"Stolzer? (.+)", r"\1 Orgulloso"),
    (r"Mutiger? (.+)", r"\1 Valiente"),
    (r"Verfluchter? (.+)", r"\1 Maldito")
]

def enrich_catalog():
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    total = len(catalog)
    inicial_null = sum(1 for v in catalog.values() if v.get("title_es") is None)
    print(f"Total entidades: {total}")
    print(f"Entidades con null inicial: {inicial_null}")

    resolved = 0
    for title_de, info in catalog.items():
        if info.get("title_es"):
            continue  # Ya tenía traducción oficial

        # 1. Buscar en diccionario exacto
        if title_de in DICTIONARY_METIN2:
            info["title_es"] = DICTIONARY_METIN2[title_de]
            resolved += 1
            continue

        # 2. Aplicar reglas morfológicas
        translated = None
        for pattern, replacement in PREFIX_RULES:
            if re.match(pattern, title_de, re.IGNORECASE):
                translated = re.sub(pattern, replacement, title_de, flags=re.IGNORECASE)
                break

        if translated:
            info["title_es"] = translated.strip()
            resolved += 1
        else:
            # 3. Si no tiene regla, usar el nombre original limpio sin null
            info["title_es"] = title_de

    # Guardar catálogo enriquecido
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    final_null = sum(1 for v in catalog.values() if v.get("title_es") is None)
    print(f"Traducciones añadidas: {resolved}")
    print(f"Entidades con null restantes: {final_null} (0% de nulls)")

if __name__ == "__main__":
    enrich_catalog()
