import json
from pathlib import Path
import requests
from pyproj import Transformer

OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

QUERY = """
[out:json][timeout:60];
area["name"="Berlin"]["admin_level"="4"]->.berlin;
(
  node["highway"="elevator"](area.berlin);
  way["highway"="elevator"](area.berlin);
  relation["highway"="elevator"](area.berlin);

  node["amenity"="elevator"](area.berlin);
  way["amenity"="elevator"](area.berlin);
  relation["amenity"="elevator"](area.berlin);
);
out center tags;
"""

# WGS84 (lon/lat) -> UTM 33N (Berlin): EPSG:25833
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25833", always_xy=True)

def to_feature(el):
    # coordinates: node has lon/lat, way/relation use center
    if el["type"] == "node":
        lon, lat = el["lon"], el["lat"]
    else:
        c = el.get("center")
        if not c:
            return None
        lon, lat = c["lon"], c["lat"]

    # transform to EPSG:25833 like your Berlin Open Data files
    x, y = transformer.transform(lon, lat)

    tags = el.get("tags", {})
    return {
        "type": "Feature",
        "id": f'elevator_{el["type"]}_{el["id"]}',
        "geometry": {"type": "Point", "coordinates": [x, y]},
        "properties": {
            "source": "osm_overpass",
            "osm_id": f'{el["type"]}/{el["id"]}',
            "wheelchair": tags.get("wheelchair"),
            "access": tags.get("access"),
            "operator": tags.get("operator"),
            "level": tags.get("level"),
            "tags": tags,
        },
    }

def main():
    data = None
    last_error = None
    
    # Versuche jeden Server in der Liste
    for url in OVERPASS_URLS:
        try:
            print(f"Versuche Server: {url}")
            r = requests.post(url, data={"data": QUERY}, timeout=120)
            r.raise_for_status()
            data = r.json()
            print(f"Erfolgreich! Server {url} hat geantwortet.")
            break
        except Exception as e:
            print(f"Fehler bei {url}: {e}")
            last_error = e
            continue
    
    if data is None:
        raise Exception(f"Alle Overpass-Server fehlgeschlagen. Letzter Fehler: {last_error}")

    features = []
    for el in data.get("elements", []):
        f = to_feature(el)
        if f:
            features.append(f)

    fc = {"type": "FeatureCollection", "features": features}

    out_path = Path("Datapoints/elevators.json")
    out_path.parent.mkdir(exist_ok=True)  # Stelle sicher, dass der Ordner existiert
    out_path.write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {len(features)} Aufzüge nach {out_path} geschrieben")

if __name__ == "__main__":
    main()