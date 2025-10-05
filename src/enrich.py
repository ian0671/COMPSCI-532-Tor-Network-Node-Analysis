# query APIs (GreyNoise, AbuseIPDB)
import requests, sqlite3, time

GN_API_KEY = "YOUR_GREYNOISE_KEY"
DB_PATH = "data/enrichment_cache.db"

def init_cache():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS greynoise(ip TEXT PRIMARY KEY, data TEXT, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.close()

def get_greynoise_info(ip):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT data FROM greynoise WHERE ip=?", (ip,))
    cached = cur.fetchone()
    if cached: return cached[0]

    r = requests.get(f"https://api.greynoise.io/v3/community/{ip}", headers={"key": GN_API_KEY})
    if r.status_code == 200:
        data = r.text
        cur.execute("INSERT OR REPLACE INTO greynoise (ip, data) VALUES (?, ?)", (ip, data))
        conn.commit()
        conn.close()
        time.sleep(1)  # Respect rate limits
        return data