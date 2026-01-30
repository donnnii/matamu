from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re, math

# FUNGSI EKSTRAK LAT LONG

def extract_lat_long(url):
    match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if match:
        return match.group(1), match.group(2)
    return None, None

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


options = Options()
# options.add_argument("--headless")  # disabled for debugging

driver = webdriver.Chrome(options=options)

#cari titik lokasi

url_lokasi = "https://www.google.com/maps/search/?api=1&query=Alun+Alun+Jepara"
driver.get(url_lokasi)

WebDriverWait(driver, 20).until(EC.url_changes(url_lokasi))

url_lokasi_final = driver.current_url

#cari titik tengah desa

url_desa = "https://www.google.com/maps/search/?api=1&query=desa+jepara+kecamatan+jepara+kabupaten+jepara"
driver.get(url_desa)

WebDriverWait(driver, 20).until(EC.url_changes(url_desa))

url_desa_final = driver.current_url

# print("URL LOKASI : ", url_lokasi_final)
# print("URL DESA : ", url_desa_final)

lat, lon = extract_lat_long(url_lokasi_final)

print("UJICOBA GEOCODE TANPA API (UNLIMITED)")
print("-------------------------------------")
print()

print("LOKASI TITIK USAHA:")
print("Latitude :", lat)
print("Longitude:", lon)
print()

lat2, lon2 = extract_lat_long(url_desa_final)

print("LOKASI TITIK TENGAH DESA:")
print("Latitude :", lat2)
print("Longitude:", lon2)
print()

distance_km = calculate_distance(lat, lon, lat2, lon2)

print("JARAK ANTARA TITIK USAHA DENGAN TENGAH DESA :", round(distance_km, 3), " km")

if distance_km < 3:
    print("Jarak Kurang dari 3km, Valid")
else:
    print("Jarak Lebih dari 3km, Not valid")

# driver.quit()
