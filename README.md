# MATAMU

**MATAMU = MApping Alamat Tanpa MUmet 😆**

MATAMU merupakan aplikasi otomatisasi untuk mengubah alamat menjadi koordinat (**Geocoding**) dengan memanfaatkan data dari **Google Maps**.

Aplikasi ini menggunakan **Selenium** sebagai alternatif dari **Google Geocoding API** yang memiliki limit pada versi gratis (±10.000 request per bulan).  
Dengan tools ini, request dapat dilakukan tanpa batasan kuota API.

Aplikasi ini bertindak sebagai **API service** yang dapat diintegrasikan dengan **n8n** atau aplikasi lain.

---

## ✨ Fitur
- Geocoding alamat otomatis (alamat → latitude & longitude)
- Menggunakan Google Maps via Selenium (tanpa API key)
- Dapat digunakan sebagai API lokal
- Siap diintegrasikan dengan n8n
- Menghitung jarak lokasi usaha ke titik tengah desa
- Validasi lokasi berdasarkan jarak

---

## ⚙️ Cara Menjalankan

Jalankan perintah berikut di Terminal / CMD:

```bash
python -m venv venv
````
```bash
venv\Scripts\activate
````
```bash
pip install selenium
````
```bash
pip install webdriver-manager
````
```bash
pip install fastapi uvicorn
````
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
````

Setelah dijalankan, API dapat diakses melalui:

```
http://localhost:8000
```

---

## 🔌 Spesifikasi API

### Endpoint

```
http://localhost:8000/geocode
```

### Metode

```
POST
```

---

## 📤 Payload (Request)

Format: **JSON**

```json
{
  "query": "nama usaha + alamat usaha",
  "desa": "nama desa",
  "kecamatan": "nama kecamatan",
  "kabupaten": "nama kabupaten"
}
```

Keterangan:

* **query** : Nama usaha + alamat lengkap
* **desa** : Nama desa lokasi usaha
* **kecamatan** : Nama kecamatan
* **kabupaten** : Nama kabupaten

Contoh: **JSON**

```json
{
  "query": "BPS Kabupaten Jepara",
  "desa": "demaan",
  "kecamatan": "jepara",
  "kabupaten": "jepara"
}
```
---

## 📥 Response

Format: **JSON**

```json
{
    "lat": "-6.6004219",
    "long": "110.6632625",
    "jarak": 0.369,
    "valid": "Y"
}
```

Keterangan:

* **lat** : Latitude hasil geocoding
* **long** : Longitude hasil geocoding
* **jarak** : Jarak titik usaha dari titik tengah desa (dalam km)
* **valid** :

  * `Y` = lokasi valid
  * `N` = lokasi tidak valid

---

## 🧩 Integrasi dengan n8n

Gunakan node **HTTP Request** dengan konfigurasi:

* Method: `POST`
* URL: `http://localhost:8000/geocode`
* Body Type: `JSON`
* Isi payload sesuai format di atas

---

## ⚠️ Catatan

* Pastikan Google Chrome terinstal
* Selenium akan membuka browser secara otomatis (headless)
* Gunakan dengan bijak untuk menghindari deteksi sebagai bot
