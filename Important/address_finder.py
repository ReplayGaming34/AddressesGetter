import csv
import os
import sys
import subprocess
from geopy.distance import geodesic
import folium
import webbrowser
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from opencage.geocoder import OpenCageGeocode
import random
import shutil

# --- Auto Install Dependencies ---
required_libs = ["geopy", "folium", "opencage"]
for lib in required_libs:
    try:
        __import__(lib)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

RADIUS_MILES = 10
HARRISBURG_COORDS = (40.2732, -76.8844)  # Harrisburg, PA

# --- Default Values (can be changed in GUI) ---
API_key = "2c3336fadeee4a56b727396cc2600b14"
EXIFTOOL_PATH = ""   # User will select
MERGED_CSV_PATH = "" # User will select
OUTPUT_FOLDER = os.path.join(os.getcwd(), "Filtered_CSVs")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def on_close():
    try:
        if os.path.isdir(OUTPUT_FOLDER):
            shutil.rmtree(OUTPUT_FOLDER)
    except Exception as e:
        print(f"Cleanup failed: {e}")
    root.destroy()


def browse_exiftool():
    path = filedialog.askopenfilename(title="Select ExifTool executable")
    if path:
        global EXIFTOOL_PATH
        EXIFTOOL_PATH = path
        exiftool_var.set(path)

def browse_csv():
    path = filedialog.askopenfilename(title="Select merged CSV file", filetypes=[("CSV Files", "*.csv")])
    if path:
        global MERGED_CSV_PATH
        MERGED_CSV_PATH = path
        csv_var.set(path)


def returnLatLon(loc):
    geocoder = OpenCageGeocode(API_key)
    results = geocoder.geocode(loc)
    if not results:
        raise ValueError(f"No results for location: {loc}")
    lat = results[0]['geometry']['lat']
    lng = results[0]['geometry']['lng']
    return lat, lng

# === GPS TAGGING ===
def set_gps_coordinates_on_image(lat, lat_ref, lon, lon_ref, file_path):
    command = [
        EXIFTOOL_PATH,
        "-overwrite_original",
        f"-GPSLatitude={lat}",
        f"-GPSLatitudeRef={lat_ref}",
        f"-GPSLongitude={lon}",
        f"-GPSLongitudeRef={lon_ref}",
        file_path
    ]
    subprocess.run(command, capture_output=True)

def load_addresses(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row.get('lat') or row.get('latitude') or row.get('y') or row.get('LAT') or 0)
                lon = float(row.get('lon') or row.get('longitude') or row.get('x') or row.get('LON') or 0)
            except ValueError:
                continue
            yield {
                'number': row.get('number') or row.get('NUMBER'),
                'street': row.get('street') or row.get('STREET'),
                'city': row.get('city') or row.get('CITY'),
                'postcode': row.get('postcode') or row.get('POSTCODE'),
                'lat': lat,
                'lon': lon
            }

def filter_addresses(addresses, street_name):
    results = []
    input_clean = street_name.strip().lower()
    for addr in addresses:
        if not addr['street'] or not addr['number']:
            continue
        addr_street_clean = addr['street'].strip().lower()
        if input_clean in addr_street_clean:
            dist = geodesic(HARRISBURG_COORDS, (addr['lat'], addr['lon'])).miles
            if dist <= RADIUS_MILES:
                results.append(addr)
    return results

def save_to_csv(addresses, street_name):
    out_csv = os.path.join(OUTPUT_FOLDER, f"filtered_{street_name.replace(' ', '_')}.csv")
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['number', 'street', 'city', 'postcode', 'lat', 'lon'])
        for a in addresses:
            writer.writerow([a['number'], a['street'], a['city'], a['postcode'], a['lat'], a['lon']])
    return out_csv

def get_gps_coordinates(image_path):
    command = [
        EXIFTOOL_PATH,
        "-GPSLatitude",
        "-GPSLatitudeRef",
        "-GPSLongitude",
        "-GPSLongitudeRef",
        image_path
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ExifTool error:\n{result.stderr}")

    lat, lat_ref, lon, lon_ref = None, None, None, None
    for line in result.stdout.splitlines():
        if "GPS Latitude Ref" in line:
            lat_ref = line.split(":")[1].strip()
        elif "GPS Latitude" in line:
            lat = line.split(":")[1].strip()
        elif "GPS Longitude Ref" in line:
            lon_ref = line.split(":")[1].strip()
        elif "GPS Longitude" in line:
            lon = line.split(":")[1].strip()

    return lat, lat_ref, lon, lon_ref

def finalize(form, files, folder):
    for i in range(len(files)):
        lat, lon = returnLatLon(form[i])
        lat_ref = "S" if lat < 0 else "N"
        lon_ref = "W" if lon < 0 else "E"

        full_path = os.path.join(folder, files[i])  # 👈 combine folder + filename

        set_gps_coordinates_on_image(abs(lat), lat_ref, abs(lon), lon_ref, full_path)

    messagebox.showinfo("Success", "Should have worked maybe👍")


def choose_addresses(filtered, files, folder):
    if not filtered:
        return []
    chosen = random.sample(filtered, min(len(files), len(filtered)))
    formatted = ""
    for i in chosen:
        formatted += f"{i['number'][:2]} {i['street']} {i['city']} PA {i['postcode'][:5]}:"
    form = formatted.split(":")
    finalize(form, files, folder)  # 👈 pass folder here


def _search_task():
    street_names = entry.get().strip().split(", ")
    if not street_names:
        messagebox.showwarning("Input Error", "Please enter a street name.")
        return

    if not os.path.isfile(MERGED_CSV_PATH):
        messagebox.showerror("Error", "Merged CSV file not found.")
        return

    status_var.set("🔄 Searching… please wait")
    root.update_idletasks()

    addresses = list(load_addresses(MERGED_CSV_PATH))

    all_results = []
    for street_name in street_names:
        filtered = filter_addresses(addresses, street_name)
        all_results.extend(filtered)

    if not all_results:
        status_var.set("❌ No results found.")
        return []

    # Save everything into one CSV
    out_csv = os.path.join(OUTPUT_FOLDER, "filtered_all.csv")
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for a in all_results:
            writer.writerow([a['number'], a['street'], a['city'], a['postcode'], a['lat'], a['lon']])

    status_var.set(f"✅ Found {len(all_results)} results total. Saved to {out_csv}.")
    return all_results


def run_search(files, folder):
    def task():
        filtered = _search_task()
        if filtered:
            choose_addresses(filtered, files, folder)
    threading.Thread(target=task, daemon=True).start()

def on_apply():
    folder = folder_path_var.get().strip()
    if not folder or not os.path.isdir(folder):
        messagebox.showerror("Error", "Please select a valid folder with images.")
        return

    files = sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    if not files:
        messagebox.showerror("Error", "No image files found in selected folder.")
        return

    run_search(files, folder)  # 👈 pass folder


# === GUI Layout ===
root = tk.Tk()
root.title("PA Address Finder")
root.geometry("600x720")   # Bigger window
root.configure(bg="#e9eef2")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("TFrame", background="#e9eef2")
style.configure("TLabel", font=("Segoe UI", 11), background="#e9eef2")
style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=8)
style.configure("TEntry", padding=6, relief="flat")

frame = ttk.Frame(root, padding=25)
frame.pack(expand=True, fill="both")

# Title
title_label = ttk.Label(frame, text="🏠 PA Address Finder Updated", font=("Segoe UI", 18, "bold"), anchor="center")
title_label.pack(pady=(0, 20))

# ExifTool
exiftool_var = tk.StringVar()
ttk.Label(frame, text="ExifTool Path:").pack(pady=(5, 0))
ttk.Entry(frame, textvariable=exiftool_var, width=55).pack(pady=5, ipady=3)
ttk.Button(frame, text="Browse", command=browse_exiftool).pack(pady=(0, 15))

# CSV
csv_var = tk.StringVar()
ttk.Label(frame, text="Merged CSV File:").pack(pady=(5, 0))
ttk.Entry(frame, textvariable=csv_var, width=55).pack(pady=5, ipady=3)
ttk.Button(frame, text="Browse", command=browse_csv).pack(pady=(0, 15))

# Image Folder
folder_path_var = tk.StringVar()
ttk.Label(frame, text="Select Folder of Images:").pack(pady=(5, 0))
folder_entry = ttk.Entry(frame, textvariable=folder_path_var, width=55)
folder_entry.pack(pady=5, ipady=3)
ttk.Button(frame, text="Browse", command=lambda: folder_path_var.set(filedialog.askdirectory())).pack(pady=(0, 15))

# Street Names
label = ttk.Label(frame, text="Enter Street Names(comma-separated):")
label.pack(pady=(5, 0))
entry = ttk.Entry(frame, width=55, font=("Segoe UI", 11))
entry.pack(pady=5, ipady=3)

# Apply Button
search_btn = ttk.Button(frame, text="Apply", command=on_apply)
search_btn.pack(pady=20)

# Status Label
status_var = tk.StringVar(value="Ready")
status_label = ttk.Label(frame, textvariable=status_var, foreground="#004080", font=("Segoe UI", 10, "italic"))
status_label.pack(pady=10)

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
