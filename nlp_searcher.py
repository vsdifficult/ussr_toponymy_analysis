import time
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
import re
from difflib import SequenceMatcher

from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass

def normalize_text(text):
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def generate_name_variants(full_name):
    variants = set()
    parts = full_name.split()
    
    if len(parts) >= 2:
        variants.add(parts[-1])
        variants.add(full_name)
        variants.add(f"{parts[0][0]}. {parts[-1]}")
        if len(parts) >= 2:
            variants.add(f"{parts[0]} {parts[-1]}")
        
        surname = parts[-1]
        if surname.endswith('ая'):
            variants.add(surname[:-2] + 'ой')
        if surname.endswith('ий'):
            variants.add(surname[:-2] + 'ого')
    
    return list(variants)

def fuzzy_match(street_name, hero_variants, threshold=0.85):
    street_normalized = normalize_text(street_name)
    
    for variant in hero_variants:
        variant_normalized = normalize_text(variant)
        
        if variant_normalized in street_normalized:
            return True
        
        ratio = SequenceMatcher(None, street_normalized, variant_normalized).ratio()
        if ratio >= threshold:
            return True
        
        street_words = street_normalized.split()
        for word in street_words:
            if len(word) > 3:  
                ratio = SequenceMatcher(None, word, variant_normalized).ratio()
                if ratio >= threshold:
                    return True
    
    return False

def extract_hero_streets(ways_result, hero_variants):
    matching_streets = []
    
    try:
        for way in ways_result.ways():
            street_name = way.tag('name')
            if street_name and fuzzy_match(street_name, hero_variants):
                matching_streets.append({
                    'name': street_name,
                    'osm_id': way.id()
                })
    except:
        pass
    
    return matching_streets


HEROES = {
    "Зоя Космодемьянская": None  
}

HEROES_VARIANTS = {}
for hero in HEROES.keys():
    HEROES_VARIANTS[hero] = generate_name_variants(hero)
    print(f"Варианты для {hero}: {HEROES_VARIANTS[hero]}")

# Список регионов РФ
RUSSIAN_REGIONS = [
    "Republic of Adygea",
    "Republic of Bashkortostan",
    "Republic of Buryatia",
    "Republic of Altai",
    "Republic of Dagestan",
    "Republic of Ingushetia",
    "Kabardino-Balkarian Republic",
    "Republic of Kalmykia",
    "Karachay-Cherkess Republic",
    "Republic of Karelia",
    "Komi Republic",
    "Republic of Crimea",
    "Republic of Mari El",
    "Republic of Mordovia",
    "Republic of Sakha",
    "Republic of North Ossetia-Alania",
    "Republic of Tatarstan",
    "Republic of Tuva",
    "Udmurt Republic",
    "Republic of Khakassia",
    "Chechen Republic",
    "Chuvash Republic",

    "Altai Krai",
    "Zabaykalsky Krai",
    "Kamchatka Krai",
    "Krasnodar Krai",
    "Krasnoyarsk Krai",
    "Perm Krai",
    "Primorsky Krai",
    "Stavropol Krai",
    "Khabarovsk Krai",

    "Amur Oblast",
    "Arkhangelsk Oblast",
    "Astrakhan Oblast",
    "Belgorod Oblast",
    "Bryansk Oblast",
    "Vladimir Oblast",
    "Volgograd Oblast",
    "Vologda Oblast",
    "Voronezh Oblast",
    "Ivanovo Oblast",
    "Irkutsk Oblast",
    "Kaliningrad Oblast",
    "Kaluga Oblast",
    "Kemerovo Oblast",
    "Kirov Oblast",
    "Kostroma Oblast",
    "Kurgan Oblast",
    "Kursk Oblast",
    "Leningrad Oblast",
    "Lipetsk Oblast",
    "Magadan Oblast",
    "Moscow Oblast",
    "Murmansk Oblast",
    "Nizhny Novgorod Oblast",
    "Novgorod Oblast",
    "Novosibirsk Oblast",
    "Omsk Oblast",
    "Orenburg Oblast",
    "Oryol Oblast",
    "Penza Oblast",
    "Pskov Oblast",
    "Rostov Oblast",
    "Ryazan Oblast",
    "Samara Oblast",
    "Saratov Oblast",
    "Sakhalin Oblast",
    "Sverdlovsk Oblast",
    "Smolensk Oblast",
    "Tambov Oblast",
    "Tver Oblast",
    "Tomsk Oblast",
    "Tula Oblast",
    "Tyumen Oblast",
    "Ulyanovsk Oblast",
    "Chelyabinsk Oblast",
    "Yaroslavl Oblast",

    "Moscow",
    "Saint Petersburg",
    "Sevastopol",

    "Jewish Autonomous Oblast",
    "Nenets Autonomous Okrug",
    "Khanty-Mansi Autonomous Okrug",
    "Chukotka Autonomous Okrug",
    "Yamalo-Nenets Autonomous Okrug"
]

nominatim = Nominatim()
overpass = Overpass()

area_ids = {}
for region in tqdm(RUSSIAN_REGIONS, desc="Получаем areaId"):
    try:
        area = nominatim.query(f"{region}, Russia")
        try:
            area_id = area.areaId()
        except AttributeError:
            area_id = area.osmId() + 3600000000
        area_ids[region] = area_id
        time.sleep(1) 
    except Exception as e:
        print(f"Ошибка при запросе {region}: {e}")
        area_ids[region] = None

data = []
detailed_streets = []

for region, area_id in tqdm(area_ids.items(), desc="Сбор статистики"):
    for hero, variants in HEROES_VARIANTS.items():
        if not area_id:
            data.append({"Регион": region, "Герой": hero, "Количество улиц": 0})
            continue

        query = f"""
        area({area_id})->.searchArea;
        (
          way["highway"]["name"~".", i](area.searchArea);
          relation["highway"]["name"~".", i](area.searchArea);
        );
        out tags;
        """
        
        try:
            result = overpass.query(query)
            
            matching_streets = extract_hero_streets(result, variants)
            count = len(matching_streets)
            
            for street in matching_streets:
                detailed_streets.append({
                    "Регион": region,
                    "Герой": hero,
                    "Название улицы": street['name'],
                    "OSM ID": street['osm_id']
                })
            
            time.sleep(1)  
            
        except Exception as e:
            print(f"Ошибка запроса Overpass для {hero} в {region}: {e}")
            count = 0

        data.append({"Регион": region, "Герой": hero, "Количество улиц": count})

df = pd.DataFrame(data)
df.to_csv("streets_by_heroes_nlp.csv", index=False, encoding='utf-8-sig')
print("Данные сохранены в streets_by_heroes_nlp.csv")

df_detailed = pd.DataFrame(detailed_streets)
if not df_detailed.empty:
    df_detailed.to_csv("streets_detailed_nlp.csv", index=False, encoding='utf-8-sig')
    print("Детальные данные сохранены в streets_detailed_nlp.csv")

plt.rcParams['font.family'] = 'DejaVu Sans'

for hero in HEROES.keys():
    df_hero = df[(df["Герой"] == hero) & (df["Количество улиц"] > 0)]
    df_hero = df_hero.sort_values("Количество улиц", ascending=True)

    if df_hero.empty:
        print(f"Нет данных для визуализации: {hero}")
        continue

    plt.figure(figsize=(12, 10))
    plt.barh(df_hero["Регион"], df_hero["Количество улиц"], color="skyblue")
    plt.title(f"Улицы в честь {hero}", fontsize=14)
    plt.xlabel("Количество улиц")
    plt.tight_layout()
    plt.savefig(f"{hero.replace(' ', '_')}_streets_nlp.png", dpi=300, bbox_inches='tight')
    plt.show()

print("\nАнализ завершен!")
print(f"Всего найдено улиц: {df['Количество улиц'].sum()}")