from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from concurrent.futures import ThreadPoolExecutor, as_completed
import mysql.connector
import re, math, urllib.parse, uuid, threading, datetime, json, asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# =========================
# CONFIG
# =========================
TELEGRAM_TOKEN = "YOUR_TOKEN_HERE"  # <--- REPLACE THIS WITH YOUR TOKEN
ALLOWED_CHAT_ID = "YOUR_CHAT_ID_HERE" # <--- REPLACE THIS WITH YOUR CHAT ID (Integer or String)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "mathca"
}

# =========================
# STATE MANAGEMENT
# =========================
class BotState:
    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.total = 0
        self.lock = threading.Lock()
        self.chat_id = None

    def reset(self):
        with self.lock:
            self.progress = 0
            self.total = 0
            self.is_running = False

    def set_running(self, running: bool):
        with self.lock:
            self.is_running = running

    def update_progress(self, current, total):
        with self.lock:
            self.progress = current
            self.total = total

    def get_status(self):
        with self.lock:
            return self.is_running, self.progress, self.total

bot_state = BotState()

# =========================
# LOGGING
# =========================
def log(msg):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    thread_name = threading.current_thread().name
    print(f"[{now}] [{thread_name}] {msg}")

# =========================
# HELPER FUNCTIONS
# =========================
def extract_latlon(url):
    coord_match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
    if coord_match:
        return coord_match.group(1), coord_match.group(2)
    fallback = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if fallback:
        return fallback.group(1), fallback.group(2)
    return None, None

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

def only_alphanumeric(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text)

# =========================
# GEOCODING PROCESS
# =========================
def process_single_row(row):
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
        driver.get("https://www.google.com/maps/search/?api=1&query=" + query3)
        WebDriverWait(driver, 20).until(lambda d: "@" in d.current_url)
        url_lokasi_final = driver.current_url

        driver.get("https://www.google.com/maps/search/?api=1&query=" + desa2)
        WebDriverWait(driver, 20).until(lambda d: "@" in d.current_url)
        url_desa_final = driver.current_url

        lat, lon = extract_latlon(url_lokasi_final)
        lat2, lon2 = extract_latlon(url_desa_final)

        jarak = calculate_distance(lat, lon, lat2, lon2)
        valid = jarak < 3

        hasil_json = json.dumps({"lat": lat, "lon": lon, "jarak_km": round(jarak, 3)})
        log(f"DONE → {idsbr} | {round(jarak,3)} km")

        return {
            "idsbr": idsbr, "lat": lat, "lon": lon, 
            "valid": valid, "hasil": hasil_json
        }
    except Exception as e:
        log(f"ERROR → {idsbr} | {e}")
        return {
            "idsbr": idsbr, "lat": None, "lon": None, 
            "valid": False, "hasil": json.dumps({"error": str(e)})
        }
    finally:
        driver.quit()

def run_geocoding_logic(app_context):
    """Refactored main logic to run in a thread"""
    log("Starting geocoding process...")
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM geocode WHERE sudah_geocode IS NULL AND nama_usaha NOT LIKE '%<%' ORDER BY idsbr ASC LIMIT 500")
        rows = cursor.fetchall()
        
        total_rows = len(rows)
        bot_state.update_progress(0, total_rows)
        
        if total_rows == 0:
            log("No data to process.")
            asyncio.run_coroutine_threadsafe(
                app_context.bot.send_message(chat_id=bot_state.chat_id, text="No data to process."),
                app_context.loop
            )
            bot_state.set_running(False)
            db.close()
            return

        executor = ThreadPoolExecutor(max_workers=10)
        futures = [executor.submit(process_single_row, row) for row in rows]
        
        completed_count = 0
        for future in as_completed(futures):
            result = future.result()
            
            if result["valid"]:
                cursor.execute("""
                    UPDATE geocode SET latitude=%s, longitude=%s, sudah_geocode='Y', hasil_geocode=%s WHERE idsbr=%s
                """, (result["lat"], result["lon"], result["hasil"], result["idsbr"]))
            else:
                cursor.execute("""
                    UPDATE geocode SET sudah_geocode='Y', hasil_geocode=%s WHERE idsbr=%s
                """, (result["hasil"], result["idsbr"]))
            
            db.commit()
            completed_count += 1
            bot_state.update_progress(completed_count, total_rows)

        cursor.close()
        db.close()
        log("Geocoding process finished.")
        
        # Send notification
        asyncio.run_coroutine_threadsafe(
            app_context.bot.send_message(chat_id=bot_state.chat_id, text="Geocoding Process Finished!"),
            app_context.loop
        )

    except Exception as e:
        log(f"Global Error: {e}")
        asyncio.run_coroutine_threadsafe(
            app_context.bot.send_message(chat_id=bot_state.chat_id, text=f"Error: {e}"),
            app_context.loop
        )
    finally:
        bot_state.set_running(False)

# =========================
# TELEGRAM HANDLERS
# =========================
async def check_auth(update: Update):
    if str(update.effective_chat.id) != str(ALLOWED_CHAT_ID):
        await update.message.reply_text("Unauthorized access.")
        log(f"Unauthorized access attempt from {update.effective_chat.id}")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text("Welcome! Use /run to start geocoding and /progress to check status.")

async def run_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return

    is_running, _, _ = bot_state.get_status()
    if is_running:
        await update.message.reply_text("Process is already running!")
        return

    bot_state.chat_id = update.effective_chat.id
    bot_state.set_running(True)
    bot_state.update_progress(0, 0)
    
    await update.message.reply_text("Starting geocoding process...")
    
    # Run in separate thread to not block bot
    threading.Thread(target=run_geocoding_logic, args=(context.application,)).start()

async def get_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    
    is_running, progress, total = bot_state.get_status()
    if not is_running:
        await update.message.reply_text("Not running.")
    else:
        await update.message.reply_text(f"Progress: {progress}/{total}")

# =========================
# MAIN ENTRY
# =========================
if __name__ == "__main__":
    if TELEGRAM_TOKEN == "YOUR_TOKEN_HERE":
        print("ERROR: Please set your TELEGRAM_TOKEN and ALLOWED_CHAT_ID in the script!")
        exit(1)
    
    if ALLOWED_CHAT_ID == "YOUR_CHAT_ID_HERE":
         print("WARNING: ALLOWED_CHAT_ID is not set. Anyone can control this bot!")

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("run", run_process))
    application.add_handler(CommandHandler("progress", get_progress))

    print("Bot is polling...")
    application.run_polling()
