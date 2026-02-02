from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor
import re, math, urllib.parse, os, uuid, threading, datetime, asyncio

app = FastAPI()

# =========================
# THREAD POOL (10 paralel)
# =========================
executor = ThreadPoolExecutor(max_workers=10)

# =========================
# LOG HELPER
# =========================
def log(msg):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    thread_name = threading.current_thread().name
    print(f"[{now}] [{thread_name}] {msg}")

# =========================
# FUNGSI EKSTRAK LAT LONG
# =========================
def extract_poi_info(google_maps_url):
    coord_match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', google_maps_url)
    lat = lon = None
    if coord_match:
        lat = coord_match.group(1)
        lon = coord_match.group(2)
    else:
        fallback = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', google_maps_url)
        if fallback:
            lat = fallback.group(1)
            lon = fallback.group(2)

    name_match = re.search(r'/place/([^/]+)/', google_maps_url)
    name = None
    if name_match:
        raw_name = name_match.group(1)
        name = urllib.parse.unquote(raw_name).replace('+', ' ')

    return name, lat, lon

# =========================
# HITUNG JARAK
# =========================
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# =========================
# CORE FUNCTION (1 JOB)
# =========================
def process_geocode(data):
    query = data["query"]
    desa = data["desa"]
    kecamatan = data["kecamatan"]
    kabupaten = data["kabupaten"]

    log(f"START → {query} | {desa}, {kabupaten}")

    query2 = query.replace(" ", "+")
    desa2 = f"desa {desa} kabupaten {kabupaten}"
    desa3 = desa2.replace(" ", "+")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    profile_dir = f"C:\\temp\\chrome_profile_{uuid.uuid4().hex}"
    options.add_argument(f"--user-data-dir={profile_dir}")

    driver = webdriver.Chrome(options=options)

    try:
        url_lokasi = "https://www.google.com/maps/search/?api=1&query=" + query2
        driver.get(url_lokasi)
        WebDriverWait(driver, 20).until(lambda d: "@" in d.current_url)
        url_lokasi_final = driver.current_url

        url_desa = "https://www.google.com/maps/search/?api=1&query=" + desa3
        driver.get(url_desa)
        WebDriverWait(driver, 20).until(lambda d: "@" in d.current_url)
        url_desa_final = driver.current_url

        name, lat, lon = extract_poi_info(url_lokasi_final)
        name2, lat2, lon2 = extract_poi_info(url_desa_final)

        distance_km = calculate_distance(lat, lon, lat2, lon2)
        valid = "Y" if distance_km < 3 else "N"

        log(f"DONE  → {query} | lat={lat}, lon={lon}, jarak={round(distance_km,3)} km, valid={valid}")

        return {
            "lat": lat,
            "long": lon,
            "jarak": round(distance_km, 3),
            "valid": valid
        }

    except TimeoutException:
        log(f"TIMEOUT → {query}")
        return {"error": "Timeout while loading Google Maps"}

    except Exception as e:
        log(f"ERROR → {query} | {str(e)}")
        return {"error": str(e)}

    finally:
        driver.quit()
        log(f"CLOSE  → {query}")

# =========================
# FASTAPI ENDPOINT
# =========================
@app.post("/geocode")
async def geocode(data: dict):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_geocode, data)
    return result
