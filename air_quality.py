import requests
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt

# Replace with your OpenWeatherMap API key
API_KEY = "297b2e12c1c5fbe636b0a34a5f9ea6bb"

def get_air_quality(city):
    try:
        # Get latitude & longitude of the city
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
        geo_response = requests.get(geo_url).json()
        if not geo_response:
            messagebox.showerror("Error", "City not found!")
            return None

        lat, lon = geo_response[0]["lat"], geo_response[0]["lon"]

        # Get air quality data
        aq_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        aq_response = requests.get(aq_url).json()
        return aq_response

    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch data: {e}")
        return None

def show_air_quality():
    city = city_entry.get()
    data = get_air_quality(city)
    if data:
        aq = data["list"][0]["main"]["aqi"]
        pollutants = data["list"][0]["components"]

        # AQI scale from OpenWeatherMap
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

        result_label.config(text=result_text)

        # Show bar chart of pollutants
        plt.bar(pollutants.keys(), pollutants.values())
        plt.title(f"Pollutants in {city}")
        plt.ylabel("µg/m³")
        plt.show()

# Tkinter GUI
root = tk.Tk()
root.title("Air Quality Dashboard")
root.geometry("400x400")

city_entry = tk.Entry(root, width=30)
city_entry.pack(pady=10)
city_entry.insert(0, "Delhi")  # default city

tk.Button(root, text="Check Air Quality", command=show_air_quality).pack(pady=10)

result_label = tk.Label(root, text="", justify="left")
result_label.pack(pady=10)

root.mainloop()
