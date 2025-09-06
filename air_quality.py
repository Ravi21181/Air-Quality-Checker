# import csv
# from datetime import datetime


# import requests
# import tkinter as tk
# from tkinter import messagebox
# import matplotlib.pyplot as plt

# # Replace with your OpenWeatherMap API key
# API_KEY = "297b2e12c1c5fbe636b0a34a5f9ea6bb"

# def get_air_quality(city):
#     try:
#         # Get latitude & longitude of the city
#         geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
#         geo_response = requests.get(geo_url).json()
#         if not geo_response:
#             messagebox.showerror("Error", "City not found!")
#             return None

#         lat, lon = geo_response[0]["lat"], geo_response[0]["lon"]

#         # Get air quality data
#         aq_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
#         aq_response = requests.get(aq_url).json()
#         return aq_response

#     except Exception as e:
#         messagebox.showerror("Error", f"Failed to fetch data: {e}")
#         return None

# def show_air_quality():
#     city = city_entry.get()
#     data = get_air_quality(city)
#     if data:
#         aq = data["list"][0]["main"]["aqi"]
#         pollutants = data["list"][0]["components"]

#                 # Save data into CSV file
#         with open("air_quality_log.csv", mode="a", newline="") as file:
#             writer = csv.writer(file)
#             now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             writer.writerow([now, city, aq, aqi_meanings[aq]] + list(pollutants.values()))


#         # AQI scale from OpenWeatherMap
#         aqi_meanings = {
#             1: "Good",
#             2: "Fair",
#             3: "Moderate",
#             4: "Poor",
#             5: "Very Poor"
#         }

#         result_text = f"Air Quality in {city}:\nAQI: {aq} ({aqi_meanings[aq]})\n\n"
#         for k, v in pollutants.items():
#             result_text += f"{k.upper()}: {v} µg/m³\n"

#         result_label.config(text=result_text)

#                 # Change text color based on AQI
#         colors = {1: "green", 2: "blue", 3: "orange", 4: "red", 5: "purple"}
#         result_label.config(text=result_text, fg=colors[aq])


#         # Show bar chart of pollutants
#         plt.bar(pollutants.keys(), pollutants.values())
#         plt.title(f"Pollutants in {city}")
#         plt.ylabel("µg/m³")
#         plt.show()

# # Tkinter GUI
# root = tk.Tk()
# root.title("Air Quality Dashboard")
# root.geometry("400x400")

# city_entry = tk.Entry(root, width=30)
# city_entry.pack(pady=10)
# city_entry.insert(0, "Delhi")  # default city

# tk.Button(root, text="Check Air Quality", command=show_air_quality).pack(pady=10)

# result_label = tk.Label(root, text="", justify="left")
# result_label.pack(pady=10)

# root.mainloop()

# def compare_cities():
#     cities = ["Delhi", "Mumbai", "London"]  # you can add more
#     aqi_values = []
    
#     for c in cities:
#         data = get_air_quality(c)
#         if data:
#             aq = data["list"][0]["main"]["aqi"]
#             aqi_values.append((c, aq))
    
#     # Bar chart comparison
#     names = [c[0] for c in aqi_values]
#     values = [c[1] for c in aqi_values]
#     plt.bar(names, values, color=["green","orange","red"])
#     plt.title("City AQI Comparison")
#     plt.show()

# # Add a button in Tkinter UI
# tk.Button(root, text="Compare Cities", command=compare_cities).pack(pady=10)

import requests
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
import csv
from datetime import datetime
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Replace with your OpenWeatherMap API key
API_KEY = "297b2e12c1c5fbe636b0a34a5f9ea6bb"

# ----------------- Fetch Air Quality Data -----------------
def get_air_quality(city):
    try:
        # Get latitude & longitude
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
        geo_response = requests.get(geo_url).json()
        if not geo_response:
            messagebox.showerror("Error", "City not found!")
            return None

        lat, lon = geo_response[0]["lat"], geo_response[0]["lon"]

        # Get air quality
        aq_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        aq_response = requests.get(aq_url).json()
        return aq_response

    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch data: {e}")
        return None

# ----------------- Show Air Quality -----------------
def show_air_quality():
    city = city_entry.get()
    data = get_air_quality(city)
    if data:
        aq = data["list"][0]["main"]["aqi"]
        pollutants = data["list"][0]["components"]

        aqi_meanings = {
            1: "Good",
            2: "Fair",
            3: "Moderate",
            4: "Poor",
            5: "Very Poor"
        }

        result_text = f"Air Quality in {city}:\nAQI: {aq} ({aqi_meanings[aq]})\n\n"
        for k, v in pollutants.items():
            result_text += f"{k.upper()}: {v} µg/m³\n"

        # Color-coded alert
        colors = {1: "green", 2: "blue", 3: "orange", 4: "red", 5: "purple"}
        result_label.config(text=result_text, fg=colors[aq])

        # Save to CSV log
        with open("air_quality_log.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([now, city, aq, aqi_meanings[aq]] + list(pollutants.values()))

        # Show pollutant bar chart
        plt.bar(pollutants.keys(), pollutants.values())
        plt.title(f"Pollutants in {city}")
        plt.ylabel("µg/m³")
        plt.show()

# ----------------- Compare Multiple Cities -----------------
def compare_cities():
    cities = ["Delhi", "Mumbai", "London"]  
    aqi_values = []

    for c in cities:
        data = get_air_quality(c)
        if data:
            aq = data["list"][0]["main"]["aqi"]
            aqi_values.append((c, aq))

    names = [c[0] for c in aqi_values]
    values = [c[1] for c in aqi_values]
    plt.bar(names, values, color=["green","orange","red"])
    plt.title("City AQI Comparison")
    plt.ylabel("AQI Level")
    plt.show()

# ----------------- Auto Update -----------------
def auto_update():
    show_air_quality()
    root.after(6000, auto_update)  # 10 minutes

# ----------------- Export PDF Report -----------------
def export_report():
    doc = SimpleDocTemplate("AirQualityReport.pdf")
    styles = getSampleStyleSheet()
    story = []

    city = city_entry.get()
    data = get_air_quality(city)
    if data:
        aq = data["list"][0]["main"]["aqi"]
        pollutants = data["list"][0]["components"]
        report_text = f"<b>Air Quality Report for {city}</b><br/>AQI: {aq}<br/>Pollutants: {pollutants}"
        story.append(Paragraph(report_text, styles["Normal"]))
        doc.build(story)
        messagebox.showinfo("Export", "Report saved as AirQualityReport.pdf")

# ----------------- Show Trend Graph -----------------
def show_trend():
    try:
        df = pd.read_csv("air_quality_log.csv", header=None)
        df.columns = ["Time", "City", "AQI", "Status", "CO", "NO", "NO2", "O3", "SO2", "PM2_5", "PM10", "NH3"]
        df["Time"] = pd.to_datetime(df["Time"])

        plt.plot(df["Time"], df["AQI"], marker="o", linestyle="-")
        plt.title("AQI Trend Over Time")
        plt.xlabel("Time")
        plt.ylabel("AQI")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
    except Exception:
        messagebox.showerror("Error", "No trend data available yet!")

# ----------------- Tkinter GUI -----------------
root = tk.Tk()
root.title("Air Quality Dashboard")
root.geometry("450x500")

city_entry = tk.Entry(root, width=30)
city_entry.pack(pady=10)
city_entry.insert(0, "Delhi")

tk.Button(root, text="Check Air Quality", command=show_air_quality).pack(pady=5)
tk.Button(root, text="Compare Cities", command=compare_cities).pack(pady=5)
tk.Button(root, text="Show Trend", command=show_trend).pack(pady=5)
tk.Button(root, text="Export Report", command=export_report).pack(pady=5)

result_label = tk.Label(root, text="", justify="left", font=("Arial", 10))
result_label.pack(pady=10)

# Start auto-update loop
auto_update()

root.mainloop()
