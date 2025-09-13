"""
Air Quality Dashboard with Data & Insights
- Compatible with Python 3.7 (32-bit)
- Uses OpenWeather API (API_KEY pre-filled)
- No voice (pyttsx3 removed for compatibility)
- Adds: Forecast summary, Top pollutant, Monthly averages, 30-day averages, Insight popup
"""

import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import sqlite3
import threading
import time
import os
import csv
from datetime import datetime, timedelta

# Optional plotting (only used if available and enabled)
try:
    import matplotlib
    matplotlib.use("Agg")  # non-GUI by default
    import matplotlib.pyplot as plt
    plotting_available = True
except Exception:
    plotting_available = False

# ------------------------
# Configuration
# ------------------------
API_KEY = "297b2e12c1c5fbe636b0a34a5f9ea6bb"  # your OpenWeather key

# Email/Push configs (optional)
EMAIL_ENABLED = False
PUSHBULLET_ENABLED = False

# Auto-monitor interval seconds
AUTO_INTERVAL = 600  # 10 minutes

# AQI alert threshold (OpenWeather scale 1-5)
AQI_THRESHOLD_ALERT = 3

# SQLite DB file
DB_FILE = "aqi_history.db"

# ------------------------
# Database helpers
# ------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        city TEXT,
        aqi INTEGER,
        status TEXT,
        co REAL, no REAL, no2 REAL, o3 REAL, so2 REAL, pm2_5 REAL, pm10 REAL, nh3 REAL,
        temp REAL, humidity REAL, wind_speed REAL
    )
    """)
    conn.commit()
    conn.close()

def save_reading_to_db(timestamp, city, aqi, status, comps, weather):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO readings (timestamp, city, aqi, status, co, no, no2, o3, so2, pm2_5, pm10, nh3,
                              temp, humidity, wind_speed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, city, aqi, status,
        comps.get("co"), comps.get("no"), comps.get("no2"), comps.get("o3"), comps.get("so2"),
        comps.get("pm2_5"), comps.get("pm10"), comps.get("nh3"),
        weather.get("temp"), weather.get("humidity"), weather.get("wind_speed")
    ))
    conn.commit()
    conn.close()

def fetch_history(limit=100, city=None):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if city:
        cur.execute("SELECT * FROM readings WHERE city=? ORDER BY timestamp DESC LIMIT ?", (city, limit))
    else:
        cur.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ------------------------
# Utilities: API fetching
# ------------------------
def get_geo(city):
    try:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
        r = requests.get(geo_url, timeout=10)
        r.raise_for_status()
        j = r.json()
        if not j:
            return None, None
        return j[0].get("lat"), j[0].get("lon")
    except Exception as e:
        print("Geo error:", e)
        return None, None

def get_current_aqi(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        j = r.json()
        if "list" not in j or not j["list"]:
            return None
        return j["list"][0]
    except Exception as e:
        print("AQI fetch error:", e)
        return None

def get_forecast_aqi(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/air_pollution/forecast?lat={lat}&lon={lon}&appid={API_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        j = r.json()
        if "list" not in j:
            return None
        return j["list"]
    except Exception as e:
        print("AQI forecast fetch error:", e)
        return None

def get_weather(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        j = r.json()
        return {
            "temp": j.get("main", {}).get("temp"),
            "humidity": j.get("main", {}).get("humidity"),
            "wind_speed": j.get("wind", {}).get("speed")
        }
    except Exception as e:
        print("Weather fetch error:", e)
        return {"temp": None, "humidity": None, "wind_speed": None}

def aqi_to_status(aqi):
    mapping = {
        1: ("Good", "0-50"),
        2: ("Fair", "51-100"),
        3: ("Moderate/Unhealthy", "101-200"),
        4: ("Poor", "201-300"),
        5: ("Very Poor/Hazardous", ">300")
    }
    return mapping.get(aqi, ("Unknown", "N/A"))

# ------------------------
# Insights functions
# ------------------------
def get_top_pollutant_from_db(city):
    """Return (pollutant, value) based on most recent DB row for city."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT co,no,no2,o3,so2,pm2_5,pm10,nh3 FROM readings WHERE city=? ORDER BY timestamp DESC LIMIT 1", (city,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None, None
    keys = ["CO", "NO", "NO2", "O3", "SO2", "PM2.5", "PM10", "NH3"]
    vals = list(row)
    # find max ignoring None
    max_idx = None
    max_val = None
    for i, v in enumerate(vals):
        if v is None:
            continue
        if max_val is None or v > max_val:
            max_val = v
            max_idx = i
    if max_idx is None:
        return None, None
    return keys[max_idx], max_val

def get_last_30days_avg(city):
    """Compute average AQI in last 30 days for city."""
    since = (datetime.now() - timedelta(days=30)).isoformat()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT AVG(aqi) FROM readings WHERE city=? AND timestamp>=?", (city, since))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def get_monthly_avg_last_12_months(city):
    """Return list of (yyyy-mm, avg_aqi) for last 12 months (may be fewer)."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # SQLite substr on ISO timestamp YYYY-MM gives first 7 chars
    cur.execute("""
        SELECT substr(timestamp,1,7) as ym, AVG(aqi) as avg_aqi
        FROM readings
        WHERE city=? AND timestamp >= ?
        GROUP BY ym
        ORDER BY ym DESC
        LIMIT 12
    """, (city, (datetime.now() - timedelta(days=365)).isoformat()))
    rows = cur.fetchall()
    conn.close()
    # return in chronological order (oldest first)
    return list(reversed(rows))

def forecast_summary(lat, lon):
    fl = get_forecast_aqi(lat, lon)
    if not fl:
        return None
    # create short summary of next up to 24 entries (or up to 24 hours)
    summary = []
    for item in fl[:24]:
        t = datetime.fromtimestamp(item.get("dt")).strftime("%Y-%m-%d %H:%M")
        a = item.get("main", {}).get("aqi")
        s, _ = aqi_to_status(a)
        summary.append((t, a, s))
    return summary

# ------------------------
# Core: fetch, log, notify (popup-only)
# ------------------------
def fetch_and_handle_city(city, popup=True, log_db=True, notify=True, do_forecast=True):
    city = city.strip()
    if not city:
        if popup:
            messagebox.showerror("Input Error", "Please enter a city name.")
        return None

    lat, lon = get_geo(city)
    if lat is None:
        if popup:
            messagebox.showerror("Geo Error", f"City '{city}' not found.")
        return None

    current = get_current_aqi(lat, lon)
    if current is None:
        if popup:
            messagebox.showerror("AQI Error", f"AQI data not available for {city}.")
        return None

    aqi = current.get("main", {}).get("aqi")
    comps = current.get("components", {})
    status, numeric_range = aqi_to_status(aqi)
    weather = get_weather(lat, lon)

    ts = datetime.now().isoformat()
    if log_db:
        save_reading_to_db(ts, city, aqi, status, comps, weather)

    # Build short popup message
    msg = f"City: {city}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nAQI (1-5): {aqi} => {status} ({numeric_range})\n\n"
    msg += "Pollutants (µg/m³):\n"
    for k in ["co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]:
        msg += f"  {k.upper()}: {comps.get(k, 'N/A')}\n"
    msg += "\nWeather:\n"
    msg += f"  Temp (°C): {weather.get('temp')}\n  Humidity: {weather.get('humidity')}\n  Wind speed: {weather.get('wind_speed')}\n"

    if popup:
        messagebox.showinfo(f"AQI: {city}", msg)

    # Alert if threshold
    if notify and aqi >= AQI_THRESHOLD_ALERT:
        messagebox.showwarning("Health Alert", f"AQI Alert for {city}: {status} ({aqi})\nTake precautions!")
        try:
            import winsound
            winsound.Beep(1000, 600)
        except Exception:
            print("\a", end="")  # bell

    # Forecast optionally
    fc = None
    if do_forecast:
        fc = forecast_summary(lat, lon)
        if fc and popup:
            fmsg = "Forecast (next points):\n" + "\n".join([f"{t}: {a} ({s})" for t, a, s in fc[:8]])
            messagebox.showinfo(f"AQI Forecast: {city}", fmsg)

    return {
        "city": city, "timestamp": ts, "aqi": aqi, "status": status,
        "components": comps, "weather": weather, "forecast": fc
    }

# ------------------------
# GUI app
# ------------------------
class AQIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Air Quality Dashboard - Insights")
        self.root.geometry("640x480")

        top = tk.Frame(root)
        top.pack(pady=8)
        tk.Label(top, text="City:").grid(row=0, column=0, padx=5)
        self.city_entry = tk.Entry(top, width=30)
        self.city_entry.grid(row=0, column=1, padx=5)
        self.city_entry.insert(0, "Delhi")

        self.check_btn = tk.Button(top, text="Check AQI", command=self.check_aqi)
        self.check_btn.grid(row=0, column=2, padx=5)

        self.insight_btn = tk.Button(top, text="Show Insights", command=self.show_insights)
        self.insight_btn.grid(row=0, column=3, padx=5)

        mid = tk.Frame(root)
        mid.pack(pady=6)
        tk.Button(mid, text="Show History", command=self.show_history_window).grid(row=0, column=0, padx=5)
        tk.Button(mid, text="Export Today's TXT", command=self.export_today_txt).grid(row=0, column=1, padx=5)
        tk.Button(mid, text="Export CSV History", command=self.export_history_csv).grid(row=0, column=2, padx=5)

        bottom = tk.Frame(root)
        bottom.pack(pady=6)
        tk.Label(bottom, text="Optional:").grid(row=0, column=0)
        tk.Button(bottom, text="Show Forecast (popup)", command=self.show_forecast_popup).grid(row=1, column=0, padx=5, pady=4)
        tk.Button(bottom, text="Top pollutant (last reading)", command=self.show_top_pollutant).grid(row=1, column=1, padx=5, pady=4)

        # Log area
        self.log_text = scrolledtext.ScrolledText(root, width=80, height=16, state="disabled")
        self.log_text.pack(pady=8)

        # Auto monitoring
        self.auto_running = False
        self.auto_thread = None
        self.auto_btn = tk.Button(root, text="Start Auto Monitor", command=self.toggle_auto)
        self.auto_btn.pack(pady=4)

    def log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def check_aqi(self):
        city = self.city_entry.get().strip()
        self.log(f"Checking AQI for {city} ...")
        res = fetch_and_handle_city(city, popup=True, log_db=True, notify=True, do_forecast=True)
        if res:
            self.log(f"Fetched: {city} AQI={res['aqi']} ({res['status']})")

    def show_insights(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Input Error", "Enter city first.")
            return

        # ensure recent reading exists: fetch current but do not popup forecast here
        res = fetch_and_handle_city(city, popup=False, log_db=True, notify=False, do_forecast=False)
        if not res:
            messagebox.showerror("Error", "Could not fetch current AQI to build insights.")
            return

        # Top pollutant from DB (most recent)
        top_pol, top_val = get_top_pollutant_from_db(city)
        # Averages
        avg_30 = get_last_30days_avg(city)
        monthly = get_monthly_avg_last_12_months(city)
        # Forecast summary
        lat, lon = get_geo(city)
        fc = forecast_summary(lat, lon) if (lat and lon) else None

        insight_msg = f"Insights for {city}\n\nCurrent AQI: {res['aqi']} ({res['status']})\n"
        insight_msg += f"Last 30 days avg AQI: {round(avg_30,2) if avg_30 else 'N/A'}\n\n"
        if monthly:
            insight_msg += "Monthly avg (last months):\n"
            for ym, v in monthly:
                insight_msg += f"  {ym}: {round(v,2)}\n"
        else:
            insight_msg += "Monthly averages: No data\n"

        if top_pol:
            insight_msg += f"\nTop pollutant (most recent reading): {top_pol} = {top_val}\n"
            # Give tailored health tip for common pollutants
            if "PM2.5" in top_pol or "PM10" in top_pol:
                insight_msg += "Health tip: PM high → wear N95 mask, avoid outdoor exercise.\n"
            elif "O3" in top_pol:
                insight_msg += "Health tip: Ozone high → sensitive groups should avoid outdoor activity midday.\n"
        else:
            insight_msg += "\nTop pollutant: N/A\n"

        if fc:
            # worst expected in forecast
            worst = max(fc, key=lambda x: (x[1] if x[1] is not None else -1))
            insight_msg += f"\nForecast sample (next points):\n"
            for t, a, s in fc[:6]:
                insight_msg += f"  {t}: {a} ({s})\n"
            insight_msg += f"\nForecast worst: {worst[0]} => {worst[1]} ({worst[2]})\n"
        else:
            insight_msg += "\nForecast: unavailable\n"

        # Show insights popup and log
        messagebox.showinfo(f"Insights: {city}", insight_msg)
        self.log(f"Insights shown for {city}")

        # Optional plotting if available (monthly avg plot)
        if plotting_available and monthly:
            try:
                months = [m for m, _ in monthly]
                vals = [v for _, v in monthly]
                plt.figure(figsize=(6,3))
                plt.plot(months, vals, marker="o")
                plt.title(f"Monthly Avg AQI (last months) - {city}")
                plt.xlabel("Month")
                plt.ylabel("Avg AQI")
                plt.xticks(rotation=45)
                plt.tight_layout()
                # save plot to file and inform user (non-blocking)
                pfile = f"monthly_avg_{city}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                plt.savefig(pfile)
                plt.close()
                self.log(f"Monthly avg plot saved: {pfile}")
                messagebox.showinfo("Plot Saved", f"Monthly average plot saved as {pfile}")
            except Exception as e:
                self.log(f"Plot error: {e}")

    def show_forecast_popup(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Enter city first.")
            return
        lat, lon = get_geo(city)
        if lat is None:
            messagebox.showerror("Geo Error", "City not found.")
            return
        fc = forecast_summary(lat, lon)
        if not fc:
            messagebox.showinfo("Forecast", "Forecast not available for this location.")
            return
        fmsg = "Forecast (next points):\n" + "\n".join([f"{t}: {a} ({s})" for t,a,s in fc[:12]])
        messagebox.showinfo(f"AQI Forecast: {city}", fmsg)
        self.log(f"Forecast shown for {city}")

    def show_top_pollutant(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Enter city first.")
            return
        pol, val = get_top_pollutant_from_db(city)
        if not pol:
            messagebox.showinfo("Top Pollutant", "No recent readings in DB to determine top pollutant.")
            return
        messagebox.showinfo("Top Pollutant", f"Top pollutant for {city}: {pol} = {val} µg/m³")
        self.log(f"Top pollutant for {city}: {pol}={val}")

    def show_history_window(self):
        rows = fetch_history(limit=500)
        win = tk.Toplevel(self.root)
        win.title("AQI History")
        txt = scrolledtext.ScrolledText(win, width=120, height=30)
        txt.pack()
        if not rows:
            txt.insert("end","No records yet.\n")
        else:
            hdr = ["id","timestamp","city","aqi","status","co","no","no2","o3","so2","pm2_5","pm10","nh3","temp","humidity","wind"]
            txt.insert("end", "\t".join(hdr)+"\n")
            for r in rows:
                txt.insert("end", "\t".join([str(c) for c in r]) + "\n")

    def export_today_txt(self):
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showerror("Error", "Enter city first.")
            return
        now = datetime.now()
        start_of_day = datetime(now.year, now.month, now.day)
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT timestamp, city, aqi, status FROM readings WHERE timestamp >= ? AND city = ? ORDER BY timestamp", (start_of_day.isoformat(), city))
        rows = cur.fetchall()
        conn.close()
        fname = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"aqi_report_{city}_{now.strftime('%Y%m%d')}.txt")
        if not fname:
            return
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"AQI Daily Report for {city}\nDate: {now.date()}\n\n")
            if not rows:
                f.write("No readings for today.\n")
            else:
                f.write("Timestamp\tCity\tAQI\tStatus\n")
                for r in rows:
                    f.write("\t".join(map(str,r)) + "\n")
        messagebox.showinfo("Exported", f"Saved TXT report: {fname}")
        self.log(f"Exported TXT report: {fname}")

    def export_history_csv(self):
        fname = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="aqi_history.csv")
        if not fname:
            return
        rows = fetch_history(limit=10000)
        hdr = ["id","timestamp","city","aqi","status","co","no","no2","o3","so2","pm2_5","pm10","nh3","temp","humidity","wind"]
        with open(fname, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(hdr)
            for r in rows:
                writer.writerow(r)
        messagebox.showinfo("Exported", f"Saved CSV history: {fname}")
        self.log(f"Exported CSV history: {fname}")

    def auto_monitor_loop(self):
        while self.auto_running:
            try:
                city = self.city_entry.get().strip()
                if city:
                    self.log("Auto-check triggered.")
                    res = fetch_and_handle_city(city, popup=False, log_db=True, notify=True, do_forecast=False)
                    if res:
                        self.log(f"Auto: {city} AQI={res['aqi']} ({res['status']})")
                else:
                    self.log("Auto-check skipped (no city).")
            except Exception as e:
                self.log(f"Auto error: {e}")
            slept = 0
            while slept < AUTO_INTERVAL and self.auto_running:
                time.sleep(1)
                slept += 1

    def toggle_auto(self):
        if not self.auto_running:
            self.auto_running = True
            self.auto_btn.configure(text="Stop Auto Monitor")
            self.auto_thread = threading.Thread(target=self.auto_monitor_loop, daemon=True)
            self.auto_thread.start()
            self.log("Auto monitoring started.")
        else:
            self.auto_running = False
            self.auto_btn.configure(text="Start Auto Monitor")
            self.log("Auto monitoring stopped.")

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = AQIApp(root)
    root.mainloop()
