from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fastapi import FastAPI
import re, math
import urllib.parse
import os

app = FastAPI()


# CLEAR CONSOLE
def cls():
    os.system('cls' if os.name=='nt' else 'clear')

cls()
print("---------------------------------------------------------------")
print("API GEOCODING READY! - HUBUNGKAN DENGAN N8N VIA PORT 8000")
print("---------------------------------------------------------------")
print()
print()

# FUNGSI EKSTRAK LAT LONG
def extract_poi_info(google_maps_url):
    """
    Extract POI dan lat/lon dari URL Google Maps.
    Returns: (name, lat, lon)
    """

    # 1. Extract POI coordinates from !3d !4d
    coord_match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', google_maps_url)
    lat = lon = None
    if coord_match:
        lat = coord_match.group(1)
        lon = coord_match.group(2)
    else:
        # fallback to @lat,lon
        fallback = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', google_maps_url)
        if fallback:
            lat = fallback.group(1)
            lon = fallback.group(2)

    # 2. Extract POI name from /place/...
    name_match = re.search(r'/place/([^/]+)/', google_maps_url)
    name = None
    if name_match:
        raw_name = name_match.group(1)
        name = urllib.parse.unquote(raw_name).replace('+', ' ')

    return name, lat, lon


#FUNGSI HITUNG JARAK DARI 2 LAT LONG

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # km
    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@app.post("/geocode")
def geocode(data: dict):
    query = data["query"]
    desa = data["desa"]
    kecamatan = data["kecamatan"]
    kabupaten = data["kabupaten"]
    
    cls()
    print("MENERIMA DATA")
    print("QUERY:")
    print(query)
    print()
    print("-------------------------------------")
    
    query2 = query.replace(" ", "+")
    
    desa2 = "desa " + desa + " kabupaten " + kabupaten
    
    desa3 = desa2.replace(" ", "+")
    
    options = Options()
    options.add_argument("--headless")  # disabled for debugging

    driver = webdriver.Chrome(options=options)

    #cari titik lokasi

    url_lokasi = "https://www.google.com/maps/search/?api=1&query=" + query2
    driver.get(url_lokasi)

    WebDriverWait(driver, 20).until(EC.url_changes(url_lokasi))

    url_lokasi_final = driver.current_url

    #cari titik tengah desa

    url_desa = "https://www.google.com/maps/search/?api=1&query=" + desa3
    driver.get(url_desa)

    WebDriverWait(driver, 20).until(EC.url_changes(url_desa))

    url_desa_final = driver.current_url

    # print("URL LOKASI : ", url_lokasi_final)
    # print("URL DESA : ", url_desa_final)

    name, lat, lon = extract_poi_info(url_lokasi_final)
    
    # CLEAR SCREEN
        
    print("BERHASIL DIPROSES")
    print("-------------------------------------")
    print()

    print("LOKASI TITIK USAHA:")
    print("Latitude :", lat)
    print("Longitude:", lon)
    print()

    name2, lat2, lon2 = extract_poi_info(url_desa_final)

    print("LOKASI TITIK TENGAH DESA:")
    print("Latitude :", lat2)
    print("Longitude:", lon2)
    print()

    distance_km = calculate_distance(lat, lon, lat2, lon2)

    print("JARAK ANTARA TITIK USAHA DENGAN TENGAH DESA :", round(distance_km, 3), " km")

    if distance_km < 3:
        print("Jarak Kurang dari 3km, Valid")
        valid = "Y"
    else:
        print("Jarak Lebih dari 3km, Not valid")
        valid = "N"
    driver.quit()
    
    print()
    print()

    if lat is None or lat is None:
        return {"error": "Could not extract coordinates"}

    return {
        "lat": lat,
        "long": lon,
        "jarak": round(distance_km, 3),
        "valid": valid
    }