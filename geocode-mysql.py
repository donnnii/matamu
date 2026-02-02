from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from concurrent.futures import ThreadPoolExecutor, as_completed
import mysql.connector
import re, math, urllib.parse, uuid, threading, datetime, json

# =========================
# MYSQL CONFIG
# =========================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "mathca"
}

# =========================
# THREAD POOL
# =========================
executor = ThreadPoolExecutor(max_workers=10)

# =========================
# LOG
# =========================
def log(msg):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    thread_name = threading.current_thread().name
    print(f"[{now}] [{thread_name}] {msg}")

# =========================
# EXTRACT LAT LONG
# =========================
def extract_latlon(url):
    coord_match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
    if coord_match:
        return coord_match.group(1), coord_match.group(2)

    fallback = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if fallback:
        return fallback.group(1), fallback.group(2)

    return None, None

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

#remove all special char
def only_alphanumeric(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text)


# =========================
# CORE FUNCTION
# =========================
def process_geocode(row):
    idsbr = row["idsbr"]
    nama = row["nama_usaha"]
    desa = row["nmdesa"]
    kab = row["nmkab"]

    log(f"START → {idsbr} | {nama}")

    query = f"{nama} desa {desa} kabupaten {kab}"
    desa_query = f"desa {desa} kabupaten {kab}"

    query2 = only_alphanumeric(query)
    
    query3 = urllib.parse.quote_plus(query2)
    
    desa2 = urllib.parse.quote_plus(desa_query)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    profile_dir = f"C:\\temp\\chrome_profile_{uuid.uuid4().hex}"
    options.add_argument(f"--user-data-dir={profile_dir}")

    driver = webdriver.Chrome(options=options)

    try:
        url_lokasi = "https://www.google.com/maps/search/?api=1&query=" + query3
        driver.get(url_lokasi)
        WebDriverWait(driver, 20).until(lambda d: "@" in d.current_url)
        url_lokasi_final = driver.current_url

        url_desa = "https://www.google.com/maps/search/?api=1&query=" + desa2
        driver.get(url_desa)
        WebDriverWait(driver, 20).until(lambda d: "@" in d.current_url)
        url_desa_final = driver.current_url

        lat, lon = extract_latlon(url_lokasi_final)
        lat2, lon2 = extract_latlon(url_desa_final)

        jarak = calculate_distance(lat, lon, lat2, lon2)
        valid = jarak < 3

        hasil_json = json.dumps({
            "lat": lat,
            "lon": lon,
            "jarak_km": round(jarak, 3)
        })

        log(f"DONE → {idsbr} | {round(jarak,3)} km")

        return {
            "idsbr": idsbr,
            "lat": lat,
            "lon": lon,
            "valid": valid,
            "hasil": hasil_json
        }

    except Exception as e:
        log(f"ERROR → {idsbr} | {e}")
        return {
            "idsbr": idsbr,
            "lat": None,
            "lon": None,
            "valid": False,
            "hasil": json.dumps({"error": str(e)})
        }

    finally:
        driver.quit()

# =========================
# MAIN
# =========================
def main():
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM geocode 
        WHERE sudah_geocode IS NULL 
        AND nama_usaha NOT LIKE '%<%' 
        ORDER BY idsbr ASC 
        LIMIT 500
    """)
    rows = cursor.fetchall()

    futures = [executor.submit(process_geocode, row) for row in rows]

    for future in as_completed(futures):
        result = future.result()

        if result["valid"]:
            cursor.execute("""
                UPDATE geocode
                SET latitude=%s,
                    longitude=%s,
                    sudah_geocode='Y',
                    hasil_geocode=%s
                WHERE idsbr=%s
            """, (result["lat"], result["lon"], result["hasil"], result["idsbr"]))
        else:
            cursor.execute("""
                UPDATE geocode
                SET sudah_geocode='Y',
                    hasil_geocode=%s
                WHERE idsbr=%s
            """, (result["hasil"], result["idsbr"]))

        db.commit()

    cursor.close()
    db.close()
    log("SELESAI SEMUA")

if __name__ == "__main__":
    main()
