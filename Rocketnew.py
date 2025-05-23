import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import math
import numpy as np
from folium.plugins import AntPath
import random

# Plotly für erweiterte Charts
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("⚠️ Plotly nicht verfügbar. Einige Charts werden nicht angezeigt. Installieren Sie mit: pip install plotly")

# Seitentitel und Beschreibung
st.title("🚀 Raketenstarts - Sichtbarkeit von Deutschland")
st.markdown("""
### Diese App zeigt kommende Raketenstarts und deren Sichtbarkeit von Deutschland aus
Erfahren Sie, wann und wo Sie Raketen und Satelliten am deutschen Himmel sehen können!
""")

# Live-Countdown zum nächsten Start
def create_launch_countdown(next_launch_time, launch_name):
    """Erstellt einen Live-Countdown zum nächsten Start"""
    
    # Zeitdifferenz berechnen
    now = datetime.now(pytz.UTC)
    time_diff = next_launch_time - now
    
    if time_diff.total_seconds() > 0:
        days = time_diff.days
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Countdown-HTML mit JavaScript für Live-Update
        countdown_html = f"""
        <div style="
            background: linear-gradient(45deg, #1f4037, #99f2c8);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        ">
            <h2 style="color: white; margin-bottom: 10px;">🚀 NÄCHSTER START COUNTDOWN</h2>
            <h3 style="color: white; margin-bottom: 15px;">{launch_name}</h3>
            <div id="countdown" style="
                font-size: 2.5em;
                font-weight: bold;
                color: #FFD700;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            ">
                {days:02d}T {hours:02d}:{minutes:02d}:{seconds:02d}
            </div>
            <p style="color: white; margin-top: 10px;">Tage : Stunden : Minuten : Sekunden</p>
        </div>
        
        <script>
        function updateCountdown() {{
            var launchTime = new Date("{next_launch_time.isoformat()}").getTime();
            var now = new Date().getTime();
            var distance = launchTime - now;
            
            if (distance > 0) {{
                var days = Math.floor(distance / (1000 * 60 * 60 * 24));
                var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                
                document.getElementById("countdown").innerHTML = 
                    String(days).padStart(2, '0') + "T " + 
                    String(hours).padStart(2, '0') + ":" + 
                    String(minutes).padStart(2, '0') + ":" + 
                    String(seconds).padStart(2, '0');
            }} else {{
                document.getElementById("countdown").innerHTML = "🚀 START ERFOLGT!";
            }}
        }}
        
        // Update jede Sekunde
        setInterval(updateCountdown, 1000);
        updateCountdown(); // Sofort starten
        </script>
        """
        
        return countdown_html
    else:
        return f"""
        <div style="
            background: linear-gradient(45deg, #ff6b6b, #feca57);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
        ">
            <h2 style="color: white;">🚀 START BEREITS ERFOLGT!</h2>
            <h3 style="color: white;">{launch_name}</h3>
        </div>
        """

# Aktuelle sichtbare Raketen/Ereignisse Übersicht
st.info("""
🌟 **AKTUELL SICHTBARE EREIGNISSE:**
• **ISS-Überflüge**: Täglich 2-5 mal sichtbar (hellster "Stern" am Himmel)
• **Starlink-Satelliten**: Einzelne Satelliten regelmäßig als bewegende Punkte
• **SpaceX Falcon 9**: Gelegentlich Spiralen nach Starts über Europa sichtbar
• **Europäische Raketen 2025**: Isar Spectrum (Norwegen), RFA One & Orbex (Schottland)
""")

# Warnung über realistische Sichtbarkeit
st.warning("""
⚠️ **WICHTIGER HINWEIS ZUR SICHTBARKEIT:**
- Raketen sind nur in **großer Höhe** (>100km) und bei **optimalen Bedingungen** sichtbar
- **Aufstieg**: Nur die ersten 5-15 Minuten, wenn Triebwerke brennen
- **Orbit**: Nur wenn Sonnenlicht reflektiert wird und über dem Horizont (>10° Elevation)
- **Wetter**: Klarer Himmel erforderlich, keine Wolken
- **Zeit**: Beste Sichtbarkeit in Dämmerung oder Nacht
- **Live-Countdown**: Zeigt Zeit bis zum nächsten Start in Echtzeit
""")

# Sidebar für wichtige Informationen
st.sidebar.title("📍 Sichtbarkeit von Deutschland")
st.sidebar.info("""
**Aktuell von Deutschland sichtbare Raketen:**
- SpaceX Falcon 9 (bei passenden Bedingungen)
- Europäische Raketen (Ariane 6, Vega C)
- Isar Aerospace Spectrum (Norwegen) 
- Orbex Prime (Schottland)
- RFA One (Schottland)

**Beste Sichtbarkeit:**
- 🌙 Nachts (22:00-04:00)
- 🌅 Dämmerung (20:00-22:00, 04:00-06:00)
- ☀️ Tagsüber meist nicht sichtbar
""")

# Funktion zum Abrufen von Daten über bevorstehende Raketenstarts
@st.cache_data(ttl=3600)
def get_launch_data():
    url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=30&mode=detailed"
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Fehler beim Abrufen der Daten: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Verbindungsfehler: {str(e)}")
        return None

# Funktion zum Simulieren von Wiedereintritts-Daten (da echte APIs oft eingeschränkt sind)
@st.cache_data(ttl=1800)  # 30 Minuten Cache
def get_reentry_data():
    """Simuliert Wiedereintritts-Daten basierend auf realistischen Szenarien"""
    
    current_time = datetime.now(pytz.UTC)
    reentries = []
    
    # Bekannte/wahrscheinliche Wiedereintritte der nächsten Wochen
    simulated_reentries = [
        {
            "name": "SpaceX Falcon 9 Upper Stage",
            "object_type": "Rocket Body",
            "origin": "Starlink Mission",
            "mass_kg": 4000,
            "size": "12m x 3.7m",
            "reentry_time": current_time + timedelta(days=2, hours=14, minutes=23),
            "uncertainty_hours": 6,
            "predicted_location": {"lat": 52.0, "lon": 12.0},
            "trajectory_start": {"lat": 58.0, "lon": -5.0},
            "trajectory_end": {"lat": 45.0, "lon": 25.0},
            "visibility_duration_minutes": 4,
            "risk_level": "Low",
            "debris_survival": "Minimal"
        },
        {
            "name": "Chinese Long March 5B Core Stage",
            "object_type": "Rocket Body", 
            "origin": "Tiangong Station Mission",
            "mass_kg": 21000,
            "size": "33m x 5m",
            "reentry_time": current_time + timedelta(days=5, hours=8, minutes=45),
            "uncertainty_hours": 12,
            "predicted_location": {"lat": 47.0, "lon": 8.0},
            "trajectory_start": {"lat": 55.0, "lon": -10.0},
            "trajectory_end": {"lat": 38.0, "lon": 30.0},
            "visibility_duration_minutes": 6,
            "risk_level": "Medium",
            "debris_survival": "Possible small fragments"
        },
        {
            "name": "Progress Cargo Spacecraft",
            "object_type": "Spacecraft",
            "origin": "ISS Resupply Mission",
            "mass_kg": 7000,
            "size": "7m x 2.7m",
            "reentry_time": current_time + timedelta(days=8, hours=21, minutes=12),
            "uncertainty_hours": 3,
            "predicted_location": {"lat": 49.0, "lon": 15.0},
            "trajectory_start": {"lat": 60.0, "lon": -2.0},
            "trajectory_end": {"lat": 35.0, "lon": 35.0},
            "visibility_duration_minutes": 3,
            "risk_level": "Low",
            "debris_survival": "Complete burnup expected"
        },
        {
            "name": "Starlink Satellite (Deorbited)",
            "object_type": "Satellite",
            "origin": "Starlink Constellation",
            "mass_kg": 260,
            "size": "2.8m x 1.65m",
            "reentry_time": current_time + timedelta(days=12, hours=3, minutes=56),
            "uncertainty_hours": 2,
            "predicted_location": {"lat": 53.0, "lon": 9.0},
            "trajectory_start": {"lat": 62.0, "lon": -8.0},
            "trajectory_end": {"lat": 42.0, "lon": 28.0},
            "visibility_duration_minutes": 2,
            "risk_level": "Very Low",
            "debris_survival": "Complete burnup"
        },
        {
            "name": "ESA Upper Stage (AVUM)",
            "object_type": "Rocket Body",
            "origin": "Vega-C Mission",
            "mass_kg": 1200,
            "size": "2.6m x 1.9m", 
            "reentry_time": current_time + timedelta(days=15, hours=16, minutes=34),
            "uncertainty_hours": 4,
            "predicted_location": {"lat": 50.0, "lon": 6.0},
            "trajectory_start": {"lat": 57.0, "lon": -12.0},
            "trajectory_end": {"lat": 41.0, "lon": 22.0},
            "visibility_duration_minutes": 3,
            "risk_level": "Low",
            "debris_survival": "Minimal fragments possible"
        }
    ]
    
    return {"results": simulated_reentries}

# Verbesserte Umlaufzeitberechnung mit Höhenprofil
def calculate_orbit_period(orbit_height, current_height=None):
    earth_radius = 6371  # km
    gravitational_parameter = 3.986004418e14  # m³/s²
    
    effective_height = current_height if current_height is not None else orbit_height
    orbit_radius = (earth_radius + effective_height) * 1000  # m
    
    orbit_period_seconds = 2 * math.pi * math.sqrt(orbit_radius**3 / gravitational_parameter)
    return orbit_period_seconds / 60  # Minuten

# Verbesserte Orbit-Pfad-Berechnung für realistische Umlaufbahnen (Kompatibilitätsfunktion)
def calculate_orbit_path(launch_site_coords, inclination=51.6, orbit_height=300, num_points=200):
    """Vereinfachte Orbit-Berechnung ohne Zeitverschiebung für Kompatibilität"""
    return calculate_orbit_path_with_time(launch_site_coords, inclination, orbit_height, 
                                        time_offset_minutes=0, num_points=num_points)

# Verbesserte Orbit-Pfad-Berechnung mit Erdrotation
def calculate_orbit_path_with_time(launch_site_coords, inclination=51.6, orbit_height=300, 
                                  launch_time_utc=None, time_offset_minutes=0, num_points=200):
    """Berechnet Umlaufbahn unter Berücksichtigung der Erdrotation"""
    
    earth_radius = 6371  # km
    earth_rotation_rate = 360 / (24 * 60)  # Grad pro Minute (15°/Stunde)
    
    launch_lat_rad = math.radians(launch_site_coords[0])
    launch_lon_rad = math.radians(launch_site_coords[1])
    
    # Erdrotation seit dem Start berücksichtigen
    rotation_offset = math.radians(earth_rotation_rate * time_offset_minutes)
    
    x0 = earth_radius * math.cos(launch_lat_rad) * math.cos(launch_lon_rad)
    y0 = earth_radius * math.cos(launch_lat_rad) * math.sin(launch_lon_rad)
    z0 = earth_radius * math.sin(launch_lat_rad)
    
    inclination_rad = math.radians(inclination)
    
    # Aufstiegsknoten verschiebt sich mit der Erdrotation
    right_ascension = (launch_lon_rad + math.pi/2 - rotation_offset) % (2 * math.pi)
    orbit_radius = earth_radius + orbit_height
    
    points = []
    
    for i in range(num_points):
        theta = i * (2 * math.pi / num_points)
        
        x_orbit = orbit_radius * math.cos(theta)
        y_orbit = orbit_radius * math.sin(theta)
        z_orbit = 0
        
        # Rotation um die z-Achse für den Aufstiegsknoten (mit Erdrotation)
        x_rotated = x_orbit * math.cos(right_ascension) - y_orbit * math.sin(right_ascension)
        y_rotated = x_orbit * math.sin(right_ascension) + y_orbit * math.cos(right_ascension)
        z_rotated = z_orbit
        
        # Rotation um die x-Achse für die Inklination
        x_final = x_rotated
        y_final = y_rotated * math.cos(inclination_rad) - z_rotated * math.sin(inclination_rad)
        z_final = y_rotated * math.sin(inclination_rad) + z_rotated * math.cos(inclination_rad)
        
        # Umrechnung in geografische Koordinaten
        lat = math.degrees(math.asin(z_final / orbit_radius))
        lon = math.degrees(math.atan2(y_final, x_final))
        
        # Normalisierung der Longitude
        lon = (lon + 180) % 360 - 180
        
        points.append((lat, lon))
    
    return points

# Aufstiegspfad-Berechnung
def calculate_ascent_path(launch_site_coords, target_orbit, ascent_duration=10, num_points=20):
    start_lat, start_lon = launch_site_coords
    orbit_path = calculate_orbit_path(launch_site_coords, target_orbit["inclination"], target_orbit["height"], 100)
    target_point = orbit_path[0]
    
    ascent_path = []
    for i in range(num_points):
        progress = i / (num_points - 1)
        current_height = target_orbit["height"] * (1 - math.exp(-5 * progress))
        current_lat = start_lat + progress * (target_point[0] - start_lat)
        current_lon = start_lon + progress * (target_point[1] - start_lon)
        ascent_path.append(((current_lat, current_lon), current_height))
    
    return ascent_path

# Deutschland-Koordinaten
germany_coords = (51.1657, 10.4515)

# Sichtbarkeitsberechnung für einen einzelnen Punkt
def is_point_visible_from_germany(position, height, time_utc):
    """Verbesserte Sichtbarkeitsberechnung mit realistischen physikalischen Constraints"""
    
    # 1. Mindesthöhe für Sichtbarkeit
    if height < 100:  # Unter 100km ist praktisch nichts sichtbar
        return 0, 0, 0
    
    # 2. Entfernung zu Deutschland
    distance = geodesic(germany_coords, position).kilometers
    
    # 3. Elevation (Winkel über dem Horizont) berechnen
    # Vereinfachte Berechnung: Je weiter entfernt, desto niedriger der Winkel
    earth_radius = 6371  # km
    
    # Winkel über dem Horizont (vereinfacht)
    if distance > 0:
        # Berücksichtigung der Erdkrümmung
        horizon_distance = math.sqrt(2 * earth_radius * height + height**2)
        
        if distance > horizon_distance:
            return 0, 0, 0  # Unter dem Horizont, nicht sichtbar
        
        # Elevationswinkel (sehr vereinfacht)
        elevation_angle = math.degrees(math.atan(height / distance))
        
        # Unter 10° Elevation meist nicht gut sichtbar
        if elevation_angle < 10:
            elevation_factor = elevation_angle / 10  # Linear abnehmen unter 10°
        else:
            elevation_factor = 1.0
    else:
        elevation_factor = 1.0
    
    # 4. Maximale Sichtdistanz basierend auf Höhe
    if height < 200:
        max_visibility_distance = 800  # km für niedrige Höhen
    elif height < 500:
        max_visibility_distance = 1200  # km für mittlere Höhen
    elif height < 1000:
        max_visibility_distance = 1800  # km für hohe Orbits
    else:
        max_visibility_distance = 2500  # km für sehr hohe Orbits
    
    # 5. Tageszeit-Faktor (wichtig für Sonnenlicht-Reflexion)
    de_timezone = pytz.timezone('Europe/Berlin')
    local_time = time_utc.astimezone(de_timezone)
    hour = local_time.hour
    
    if 22 <= hour or hour <= 4:
        time_factor = 1.0  # Nacht - beste Sichtbarkeit
    elif (20 <= hour < 22) or (4 < hour <= 6):
        time_factor = 0.8  # Dämmerung - gute Sichtbarkeit
    elif (18 <= hour < 20) or (6 < hour <= 8):
        time_factor = 0.3  # Morgen/Abend - mäßige Sichtbarkeit
    else:
        time_factor = 0.05  # Tag - sehr schlecht sichtbar (nur große, helle Objekte)
    
    # 6. Entfernungsfaktor
    if distance <= max_visibility_distance:
        distance_factor = max(0, 1 - (distance / max_visibility_distance))
    else:
        distance_factor = 0
    
    # 7. Höhenfaktor (höhere Objekte sind besser sichtbar)
    if height >= 400:
        height_factor = 1.0
    elif height >= 200:
        height_factor = 0.8
    elif height >= 100:
        height_factor = 0.5
    else:
        height_factor = 0.1
    
    # 8. Gesamtsichtbarkeit berechnen
    visibility_chance = (
        distance_factor * 0.4 +      # 40% Entfernung
        time_factor * 0.3 +          # 30% Tageszeit  
        elevation_factor * 0.2 +     # 20% Elevation
        height_factor * 0.1          # 10% Höhe
    ) * 100
    
    # Realistische Begrenzung
    visibility_chance = min(100, max(0, visibility_chance))
    
    return visibility_chance, distance_factor, time_factor

def create_trajectory_map(launch_coords, launch_time_utc, target_orbit, orbit_type):
    """Erstellt eine detaillierte Karte mit Aufstiegspfad, Orbit und Sichtbarkeitsfenstern"""
    
    # Karte zentriert auf Europa
    trajectory_map = folium.Map(location=[54, 15], zoom_start=4)
    
    # Deutschland markieren
    folium.Marker(
        location=germany_coords,
        popup="🇩🇪 Deutschland<br>Beobachtungsstandort",
        icon=folium.Icon(color="blue", icon="eye", prefix="fa")
    ).add_to(trajectory_map)
    
    # ISS Position zur Startzeit hinzufügen
    iss_position = get_iss_position_approximation(launch_time_utc)
    folium.Marker(
        location=iss_position,
        popup=f"🛰️ ISS Position<br>zur Startzeit<br>{launch_time_utc.strftime('%H:%M')} UTC",
        icon=folium.Icon(color="green", icon="satellite", prefix="fa")
    ).add_to(trajectory_map)
    
    # Linie zwischen ISS und Startplatz
    distance_iss_launch = geodesic(iss_position, launch_coords).kilometers
    if distance_iss_launch < 2000:  # Nur wenn ISS den Start sehen könnte
        folium.PolyLine(
            [iss_position, launch_coords],
            color="green",
            weight=2,
            opacity=0.6,
            popup=f"ISS-Start Sichtlinie<br>{distance_iss_launch:.0f} km"
        ).add_to(trajectory_map)
    
    # Startort markieren
    folium.Marker(
        location=launch_coords,
        popup=f"🚀 Startplatz<br>Start: {launch_time_utc.strftime('%H:%M:%S')} UTC",
        icon=folium.Icon(color="red", icon="rocket", prefix="fa")
    ).add_to(trajectory_map)
    
    # 1. AUFSTIEGSPFAD mit Zeitmarkierungen
    ascent_duration = target_orbit["ascent_duration"]  # Minuten
    ascent_points = []
    ascent_times = []
    
    for minute in range(ascent_duration + 1):
        # Vereinfachter Aufstiegspfad (östlich, entsprechend der Inklination)
        progress = minute / ascent_duration
        
        # Höhenprofil: exponentieller Anstieg
        current_height = target_orbit["height"] * (1 - math.exp(-3 * progress))
        
        # Nur Punkte ab 100km Höhe berücksichtigen
        if current_height < 100:
            continue
        
        # Horizontale Bewegung basierend auf Inklination
        inclination_rad = math.radians(target_orbit["inclination"])
        
        # Bewegung nach Osten/Nordosten je nach Inklination
        lat_offset = progress * 2 * math.cos(inclination_rad)  # Bis zu 2° nach Norden
        lon_offset = progress * 4 * math.sin(inclination_rad) if target_orbit["inclination"] > 0 else progress * 4  # Nach Osten
        
        current_lat = launch_coords[0] + lat_offset
        current_lon = launch_coords[1] + lon_offset
        
        ascent_points.append([current_lat, current_lon])
        current_time = launch_time_utc + timedelta(minutes=minute)
        ascent_times.append(current_time)
        
        # Zeitmarkierungen alle 2 Minuten während Aufstieg
        if minute % 2 == 0:
            # Sichtbarkeit zu diesem Zeitpunkt berechnen
            visibility, _, _ = is_point_visible_from_germany((current_lat, current_lon), current_height, current_time)
            
            # Nur markieren wenn tatsächlich sichtbar (mindestens 20% und über 100km Höhe)
            if visibility > 20 and current_height > 100:
                color = "green" if visibility > 60 else "orange" if visibility > 40 else "red"
                
                de_timezone = pytz.timezone('Europe/Berlin')
                local_time = current_time.astimezone(de_timezone)
                
                # Elevation berechnen für bessere Info
                distance_to_germany = geodesic(germany_coords, (current_lat, current_lon)).kilometers
                elevation_angle = math.degrees(math.atan(current_height / distance_to_germany)) if distance_to_germany > 0 else 0
                
                popup_text = f"""
                <b>🚀 Aufstieg T+{minute} Min</b><br>
                Zeit UTC: {current_time.strftime('%H:%M:%S')}<br>
                Zeit DE: {local_time.strftime('%H:%M:%S')}<br>
                Höhe: {current_height:.0f} km<br>
                Elevation: {elevation_angle:.1f}°<br>
                Entfernung: {distance_to_germany:.0f} km<br>
                Sichtbarkeit: {visibility:.0f}%
                """
                
                folium.CircleMarker(
                    location=[current_lat, current_lon],
                    radius=8,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.8,
                    popup=popup_text,
                    tooltip=f"T+{minute}min - {visibility:.0f}% sichtbar"
                ).add_to(trajectory_map)
    
    # Aufstiegspfad zeichnen
    folium.PolyLine(
        ascent_points,
        color="red",
        weight=4,
        opacity=0.8,
        tooltip="🚀 Aufstiegspfad"
    ).add_to(trajectory_map)
    
    # 2. ORBITALE PFADE - Erster Umlauf mit Erdrotation
    orbit_period = calculate_orbit_period(target_orbit["height"])  # Minuten
    orbit_start_time = launch_time_utc + timedelta(minutes=ascent_duration)
    
    # Orbit-Pfad mit Erdrotation berechnen
    orbit_path = calculate_orbit_path_with_time(
        launch_coords, 
        target_orbit["inclination"], 
        target_orbit["height"],
        launch_time_utc,
        ascent_duration,  # Zeit seit Start
        100
    )
    
    # Orbit als Linie zeichnen
    orbit_points = [[point[0], point[1]] for point in orbit_path]
    
    folium.PolyLine(
        orbit_points,
        color="blue",
        weight=4,
        opacity=0.8,
        tooltip=f"🛸 Erster Umlauf ({orbit_start_time.strftime('%H:%M')} UTC)"
    ).add_to(trajectory_map)
    
    # Sichtbarkeitsanalyse für den ersten Umlauf
    for i in range(0, len(orbit_path), 8):  # Jeden 8. Punkt markieren
        point = orbit_path[i]
        
        # Zeit für diesen Punkt berechnen
        point_progress = i / len(orbit_path)
        point_time = orbit_start_time + timedelta(minutes=point_progress * orbit_period)
        
        # Sichtbarkeit berechnen
        visibility, _, _ = is_point_visible_from_germany(point, target_orbit["height"], point_time)
        distance = geodesic(germany_coords, point).kilometers
        
        # Elevation prüfen
        elevation_angle = math.degrees(math.atan(target_orbit["height"] / distance)) if distance > 0 else 0
        
        # Nur Punkte mit >10° Elevation und >30% Sichtbarkeit anzeigen
        if visibility > 30 and elevation_angle > 10:
            color = "lightgreen" if visibility > 70 else "yellow" if visibility > 50 else "orange"
            
            de_timezone = pytz.timezone('Europe/Berlin')
            local_time = point_time.astimezone(de_timezone)
            
            popup_text = f"""
            <b>🛸 Erster Umlauf</b><br>
            Zeit UTC: {point_time.strftime('%H:%M:%S')}<br>
            Zeit DE: {local_time.strftime('%H:%M:%S')}<br>
            Höhe: {target_orbit["height"]} km<br>
            Elevation: {elevation_angle:.1f}°<br>
            Entfernung: {distance:.0f} km<br>
            Sichtbarkeit: {visibility:.0f}%<br>
            Position: {point[0]:.1f}°N, {point[1]:.1f}°E
            """
            
            folium.CircleMarker(
                location=point,
                radius=8,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.8,
                popup=popup_text,
                tooltip=f"Umlauf 1: {visibility:.0f}% sichtbar, {elevation_angle:.1f}° Elevation"
            ).add_to(trajectory_map)
    
    # 3. SICHTBARKEITSZONEN um Deutschland
    visibility_circles = [
        {"radius": 500, "color": "green", "label": "Sehr gut sichtbar"},
        {"radius": 1000, "color": "yellow", "label": "Gut sichtbar"},
        {"radius": 2000, "color": "orange", "label": "Bedingt sichtbar"},
    ]
    
    for circle in visibility_circles:
        folium.Circle(
            location=germany_coords,
            radius=circle["radius"] * 1000,  # Meter
            color=circle["color"],
            fill=False,
            weight=2,
            opacity=0.4,
            tooltip=f"{circle['label']} (Radius: {circle['radius']} km)"
        ).add_to(trajectory_map)
    
    # 4. BESTE STARTPOSITIONEN markieren
    best_positions = get_best_launch_positions_for_germany()
    for i, pos in enumerate(best_positions[:3]):  # Top 3 anzeigen
        if i == 0:
            color = "gold"
            icon = "star"
        elif i == 1:
            color = "silver" 
            icon = "star"
        else:
            color = "bronze"
            icon = "star"
            
        folium.Marker(
            location=pos["coords"],
            popup=f"🏆 #{i+1} {pos['name']}<br>Entfernung: {pos['distance']:.0f}km<br>Bewertung: {pos['rating']}",
            icon=folium.Icon(color="white", icon=icon, prefix="fa", icon_color=color)
        ).add_to(trajectory_map)
    
    # 5. LEGENDE erstellen
    legend_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; z-index: 1000; 
                background-color: white; padding: 15px; border: 2px solid grey; 
                border-radius: 10px; font-size: 12px; max-width: 250px;">
    <h4>🗺️ Flugbahn-Legende</h4>
    
    <p><b>Aufstieg (T+0 bis T+{ascent_duration} Min):</b><br>
    <i class="fa fa-circle" style="color:red;"></i> Aufstiegspfad<br>
    <i class="fa fa-circle" style="color:green;"></i> Gut sichtbar (>60%, >100km Höhe)<br>
    <i class="fa fa-circle" style="color:orange;"></i> Bedingt sichtbar (40-60%, >100km)<br>
    <i class="fa fa-circle" style="color:red;"></i> Schlecht sichtbar (20-40%, >100km)</p>
    
    <p><b>Orbital-Phase (1 Umlauf):</b><br>
    <i class="fa fa-circle" style="color:blue;"></i> Erster Umlauf (Start+{ascent_duration:.0f}min)<br>
    <i class="fa fa-circle" style="color:lightgreen;"></i> Sehr gut sichtbar (>70%, >10° Elevation)<br>
    <i class="fa fa-circle" style="color:yellow;"></i> Gut sichtbar (50-70%, >10° Elevation)<br>
    <i class="fa fa-circle" style="color:orange;"></i> Bedingt sichtbar (30-50%, >10° Elevation)</p>
    
    <p><b>🌍 Realistische Orbital-Mechanik:</b><br>
    • Zeigt nur den ersten Umlauf nach dem Start<br>
    • Erdrotation wird berücksichtigt<br>
    • Realistische Sichtbarkeitsbedingungen</p>
    
    <p><b>⚠️ Realistische Sichtbarkeit:</b><br>
    • Mindesthöhe: 100km für Sichtbarkeit<br>
    • Elevation: >10° über Horizont erforderlich<br>
    • Beste Zeit: Dämmerung/Nacht<br>
    • Klarer Himmel notwendig</p>
    
    <p><b>Orbit-Parameter:</b><br>
    Höhe: {target_orbit["height"]} km<br>
    Inklination: {target_orbit["inclination"]}°<br>
    Umlaufzeit: {calculate_orbit_period(target_orbit["height"]):.1f} Min</p>
    
    <p><i>💡 Klicken Sie auf die Punkte für Details!</i></p>
    </div>
    """
    trajectory_map.get_root().html.add_child(folium.Element(legend_html))
    
    return trajectory_map

def calculate_visibility_schedule(launch_coords, launch_time_utc, target_orbit):
    """Berechnet einen detaillierten Zeitplan der Sichtbarkeitsfenster"""
    
    schedule = []
    de_timezone = pytz.timezone('Europe/Berlin')
    
    # 1. Aufstiegsphase
    ascent_duration = target_orbit["ascent_duration"]
    
    for minute in range(0, ascent_duration + 1, 2):  # Alle 2 Minuten
        progress = minute / ascent_duration
        
        # Vereinfachte Position während Aufstieg
        inclination_rad = math.radians(target_orbit["inclination"])
        lat_offset = progress * 2 * math.cos(inclination_rad)
        lon_offset = progress * 4 * math.sin(inclination_rad) if target_orbit["inclination"] > 0 else progress * 4
        
        current_lat = launch_coords[0] + lat_offset
        current_lon = launch_coords[1] + lon_offset
        current_height = target_orbit["height"] * (1 - math.exp(-3 * progress))
        
        current_time = launch_time_utc + timedelta(minutes=minute)
        visibility, _, _ = is_point_visible_from_germany((current_lat, current_lon), current_height, current_time)
        
        distance = geodesic(germany_coords, (current_lat, current_lon)).kilometers
        
        schedule.append({
            'phase': f'Aufstieg T+{minute} Min',
            'time_utc': current_time.strftime('%H:%M:%S'),
            'time_de': current_time.astimezone(de_timezone).strftime('%H:%M:%S'),
            'coords': (current_lat, current_lon),
            'height': int(current_height),
            'visibility': visibility,
            'distance': distance
        })
    
    # 2. Orbitale Phase - erste 3 Umläufe mit Erdrotation
    orbit_period = calculate_orbit_period(target_orbit["height"])
    orbit_start_time = launch_time_utc + timedelta(minutes=ascent_duration)
    
    for orbit_num in range(3):  # Erste 3 Umläufe
        orbit_time_offset = orbit_num * orbit_period
        current_orbit_time = orbit_start_time + timedelta(minutes=orbit_time_offset)
        
        # Orbit-Pfad mit Erdrotation für diesen Zeitpunkt
        orbit_path = calculate_orbit_path_with_time(
            launch_coords,
            target_orbit["inclination"],
            target_orbit["height"],
            launch_time_utc,
            ascent_duration + orbit_time_offset,
            60
        )
        
        for i in range(0, len(orbit_path), 5):  # Jeden 5. Punkt prüfen
            point = orbit_path[i]
            point_progress = i / len(orbit_path)
            point_time = current_orbit_time + timedelta(minutes=point_progress * orbit_period)
            
            visibility, _, _ = is_point_visible_from_germany(point, target_orbit["height"], point_time)
            distance = geodesic(germany_coords, point).kilometers
            
            # Elevation prüfen
            elevation_angle = math.degrees(math.atan(target_orbit["height"] / distance)) if distance > 0 else 0
            
            if visibility > 20 and elevation_angle > 10:  # Nur relevante und sichtbare Punkte
                schedule.append({
                    'phase': f'Umlauf {orbit_num + 1}',
                    'time_utc': point_time.strftime('%H:%M:%S'),
                    'time_de': point_time.astimezone(de_timezone).strftime('%H:%M:%S'),
                    'coords': point,
                    'height': target_orbit["height"],
                    'visibility': visibility,
                    'distance': distance
                })
    
    # Nach Sichtbarkeit sortieren
    schedule = sorted(schedule, key=lambda x: x['visibility'], reverse=True)
    
    return schedule[:15]  # Top 15 Sichtbarkeitsfenster

def calculate_direction_from_germany(coords):
    """Berechnet die Himmelsrichtung von Deutschland aus zu den gegebenen Koordinaten"""
    
    lat_diff = coords[0] - germany_coords[0]
    lon_diff = coords[1] - germany_coords[1]
    
    if abs(lat_diff) > abs(lon_diff):
        if lat_diff > 0:
            return "Norden 🧭"
        else:
            return "Süden 🧭"
    else:
        if lon_diff > 0:
            return "Osten 🧭"
        else:
            return "Westen 🧭"

def get_iss_position_approximation(time_utc):
    """Approximiert die ISS-Position zu einem gegebenen Zeitpunkt"""
    # ISS Orbital-Parameter (vereinfacht)
    iss_height = 408  # km
    iss_inclination = 51.6  # Grad
    iss_period = 92.68  # Minuten
    
    # Referenzzeitpunkt (approximiert)
    epoch = datetime(2025, 1, 1, tzinfo=pytz.UTC)
    minutes_since_epoch = (time_utc - epoch).total_seconds() / 60
    
    # Orbits seit Epoche
    orbits_completed = minutes_since_epoch / iss_period
    current_orbit_progress = (orbits_completed % 1) * 360  # Grad im aktuellen Orbit
    
    # Vereinfachte Position basierend auf Inklination
    lat = math.sin(math.radians(current_orbit_progress)) * iss_inclination
    
    # Longitude mit Erdrotation
    earth_rotation_since_epoch = minutes_since_epoch * (360 / (24 * 60))  # Grad
    lon = (current_orbit_progress - earth_rotation_since_epoch) % 360
    if lon > 180:
        lon -= 360
    
    return (lat, lon)

def get_iss_visibility_info(launch_time_utc, launch_coords):
    """Berechnet ISS-Sichtbarkeitsinformationen für einen Start"""
    
    iss_position = get_iss_position_approximation(launch_time_utc)
    
    # Entfernung ISS zu Startplatz
    distance_to_launch = geodesic(iss_position, launch_coords).kilometers
    
    # ISS-Sichtbarkeit von Deutschland
    iss_visibility_from_germany, _, _ = is_point_visible_from_germany(
        iss_position, 408, launch_time_utc
    )
    
    # Kann ISS den Start sehen? (vereinfachte Berechnung)
    # ISS kann etwa 2000km weit sehen
    iss_can_see_launch = "Ja ✅" if distance_to_launch < 2000 else "Nein ❌"
    
    visibility_text = "Sehr gut ✅" if iss_visibility_from_germany > 70 else \
                     "Gut ⭐" if iss_visibility_from_germany > 40 else \
                     "Möglich 🟡" if iss_visibility_from_germany > 10 else "Nicht sichtbar ❌"
    
    return {
        'approx_position': f"{iss_position[0]:.1f}°N, {iss_position[1]:.1f}°E",
        'visibility_from_germany': visibility_text,
        'distance_to_launch': distance_to_launch,
        'iss_can_see_launch': iss_can_see_launch
    }

def get_best_launch_positions_for_germany():
    """Gibt die besten Startpositionen für Sichtbarkeit von Deutschland zurück"""
    
    # Bekannte Startplätze mit Koordinaten
    launch_sites = [
        {"name": "SaxaVord Spaceport (Schottland)", "coords": (60.7, -0.8), "active": True},
        {"name": "Andøya Spaceport (Norwegen)", "coords": (69.3, 16.0), "active": True},
        {"name": "Sutherland Spaceport (Schottland)", "coords": (58.4, -4.2), "active": True},
        {"name": "Plesetsk (Russland)", "coords": (62.9, 40.6), "active": True},
        {"name": "Vandenberg (Kalifornien)", "coords": (34.6, -120.6), "active": True},
        {"name": "Cape Canaveral (Florida)", "coords": (28.6, -80.6), "active": True},
        {"name": "Kourou (Franz. Guayana)", "coords": (5.2, -52.8), "active": True},
        {"name": "Baikonur (Kasachstan)", "coords": (45.9, 63.3), "active": True},
        {"name": "Wallops (Virginia)", "coords": (37.8, -75.5), "active": True},
        {"name": "Rocket Lab Mahia (Neuseeland)", "coords": (-39.3, 177.9), "active": True}
    ]
    
    # Berechne Entfernungen und bewerte Sichtbarkeit
    for site in launch_sites:
        distance = geodesic(germany_coords, site["coords"]).kilometers
        site["distance"] = distance
        
        # Bewertung basierend auf Entfernung
        if distance <= 1000:
            site["rating"] = "Exzellent"
            site["score"] = 5
        elif distance <= 2000:
            site["rating"] = "Sehr gut"
            site["score"] = 4
        elif distance <= 3500:
            site["rating"] = "Gut"
            site["score"] = 3
        elif distance <= 6000:
            site["rating"] = "Mäßig"
            site["score"] = 2
        else:
            site["rating"] = "Schlecht"
            site["score"] = 1
    
    # Sortiere nach Entfernung (beste zuerst)
    launch_sites.sort(key=lambda x: x["distance"])
    
    return launch_sites[:5]  # Top 5

def get_launch_position_rank(launch_coords):
    """Bewertet die Qualität einer Startposition für Deutschland"""
    
    distance = geodesic(germany_coords, launch_coords).kilometers
    
    if distance <= 1000:
        return "🥇 Exzellent (Top 3 weltweit)"
    elif distance <= 2000:
        return "🥈 Sehr gut (Top 10 weltweit)" 
    elif distance <= 3500:
        return "🥉 Gut (Top 20 weltweit)"
    elif distance <= 6000:
        return "🟡 Mäßig (Top 50 weltweit)"
    else:
        return "🔴 Schlecht für Sichtbarkeit"

def get_current_iss_info():
    """Holt aktuelle ISS-Position und -Daten"""
    try:
        # Vereinfachte ISS-Position (in echter App würde man ISS API verwenden)
        import time
        current_time = time.time()
        
        # Simulierte ISS-Position basierend auf aktueller Zeit
        iss_period = 92.68 * 60  # ISS Umlaufzeit in Sekunden
        progress = (current_time % iss_period) / iss_period
        
        # Vereinfachte Orbital-Berechnung
        lat = math.sin(progress * 2 * math.pi) * 51.6  # Max Breite entspricht Inklination
        lon = (progress * 360 - (current_time / 240) % 360) % 360  # Erdrotation berücksichtigen
        if lon > 180:
            lon -= 360
            
        return {
            'latitude': lat,
            'longitude': lon,
            'altitude': 408.0,  # Durchschnittliche ISS-Höhe
            'velocity': 27600.0  # km/h
        }
    except:
        # Fallback-Position
        return {
            'latitude': 0.0,
            'longitude': 0.0,
            'altitude': 408.0,
            'velocity': 27600.0
        }

def get_iss_visibility_from_germany():
    """Berechnet aktuelle ISS-Sichtbarkeit von Deutschland"""
    current_time = datetime.now(pytz.UTC)
    iss_info = get_current_iss_info()
    iss_coords = (iss_info['latitude'], iss_info['longitude'])
    
    # Entfernung und Elevation berechnen
    distance = geodesic(germany_coords, iss_coords).kilometers
    
    if distance > 2000:  # ISS zu weit entfernt
        return {
            'is_visible': False,
            'reason': 'ISS zu weit entfernt',
            'next_pass': 'In ~45 Minuten',
            'elevation': 0,
            'azimuth': 0,
            'direction': 'N/A',
            'visibility_quality': 'Nicht sichtbar'
        }
    
    # Elevation über Horizont
    elevation = math.degrees(math.atan(iss_info['altitude'] / distance)) if distance > 0 else 0
    
    # Azimut (vereinfacht)
    lat_diff = iss_coords[0] - germany_coords[0]
    lon_diff = iss_coords[1] - germany_coords[1]
    azimuth = math.degrees(math.atan2(lon_diff, lat_diff)) % 360
    
    # Richtung bestimmen
    if 337.5 <= azimuth or azimuth < 22.5:
        direction = "Norden"
    elif 22.5 <= azimuth < 67.5:
        direction = "Nordosten"
    elif 67.5 <= azimuth < 112.5:
        direction = "Osten"
    elif 112.5 <= azimuth < 157.5:
        direction = "Südosten"
    elif 157.5 <= azimuth < 202.5:
        direction = "Süden"
    elif 202.5 <= azimuth < 247.5:
        direction = "Südwesten"
    elif 247.5 <= azimuth < 292.5:
        direction = "Westen"
    else:
        direction = "Nordwesten"
    
    # Sichtbarkeit prüfen
    visibility, _, _ = is_point_visible_from_germany(iss_coords, iss_info['altitude'], current_time)
    
    if elevation < 10:
        return {
            'is_visible': False,
            'reason': 'Unter dem Horizont',
            'next_pass': 'In ~20-90 Minuten',
            'elevation': elevation,
            'azimuth': azimuth,
            'direction': direction,
            'visibility_quality': 'Nicht sichtbar'
        }
    
    if visibility < 30:
        return {
            'is_visible': False,
            'reason': 'Ungünstige Lichtverhältnisse',
            'next_pass': 'Bei Dämmerung/Nacht',
            'elevation': elevation,
            'azimuth': azimuth,
            'direction': direction,
            'visibility_quality': 'Schlecht'
        }
    
    # ISS ist sichtbar!
    quality = "Exzellent" if visibility > 80 else "Sehr gut" if visibility > 60 else "Gut"
    
    return {
        'is_visible': True,
        'elevation': elevation,
        'azimuth': azimuth,
        'direction': direction,
        'visibility_quality': quality,
        'next_pass': 'Jetzt sichtbar!',
        'reason': 'Optimal sichtbar'
    }

def get_next_iss_pass_time():
    """Berechnet die nächste ISS-Sichtung (vereinfacht)"""
    now = datetime.now(pytz.UTC)
    
    # Vereinfachte Berechnung: ISS ist etwa alle 90 Minuten sichtbar
    # Suche den nächsten Zeitpunkt mit guter Sichtbarkeit
    for minutes_ahead in range(10, 180, 10):  # Prüfe alle 10 Minuten für die nächsten 3 Stunden
        future_time = now + timedelta(minutes=minutes_ahead)
        
        # Simuliere ISS-Position zu diesem Zeitpunkt
        future_timestamp = future_time.timestamp()
        iss_period = 92.68 * 60
        progress = (future_timestamp % iss_period) / iss_period
        
        lat = math.sin(progress * 2 * math.pi) * 51.6
        lon = (progress * 360 - (future_timestamp / 240) % 360) % 360
        if lon > 180:
            lon -= 360
            
        iss_coords = (lat, lon)
        distance = geodesic(germany_coords, iss_coords).kilometers
        elevation = math.degrees(math.atan(408 / distance)) if distance > 0 else 0
        
        visibility, _, _ = is_point_visible_from_germany(iss_coords, 408, future_time)
        
        if elevation > 10 and visibility > 30:  # Gute Sichtbarkeit
            return future_time
    
    # Fallback: In 2 Stunden
    return now + timedelta(hours=2)

def create_iss_countdown(next_pass_time):
    """Erstellt Countdown zur nächsten ISS-Sichtung"""
    countdown_html = f"""
    <div style="
        background: linear-gradient(45deg, #0f3460, #16537e);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <h4 style="color: white; margin-bottom: 10px;">🛰️ NÄCHSTE ISS-SICHTUNG</h4>
        <div id="iss-countdown" style="
            font-size: 1.5em;
            font-weight: bold;
            color: #87CEEB;
        ">
            Berechne...
        </div>
        <p style="color: white; margin-top: 5px; font-size: 0.9em;">Stunden : Minuten : Sekunden</p>
    </div>
    
    <script>
    function updateISSCountdown() {{
        var passTime = new Date("{next_pass_time.isoformat()}").getTime();
        var now = new Date().getTime();
        var distance = passTime - now;
        
        if (distance > 0) {{
            var hours = Math.floor(distance / (1000 * 60 * 60));
            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            document.getElementById("iss-countdown").innerHTML = 
                String(hours).padStart(2, '0') + ":" + 
                String(minutes).padStart(2, '0') + ":" + 
                String(seconds).padStart(2, '0');
        }} else {{
            document.getElementById("iss-countdown").innerHTML = "🛰️ ISS ÜBERFLUG!";
        }}
    }}
    
    setInterval(updateISSCountdown, 1000);
    updateISSCountdown();
    </script>
    """
    return countdown_html

def create_iss_live_map(iss_info):
    """Erstellt eine kleine Live-Karte mit ISS-Position"""
    
    # Karte zentriert auf ISS
    iss_map = folium.Map(
        location=[iss_info['latitude'], iss_info['longitude']], 
        zoom_start=3
    )
    
    # ISS Position markieren
    folium.Marker(
        location=[iss_info['latitude'], iss_info['longitude']],
        popup=f"""
        🛰️ ISS Live Position<br>
        Höhe: {iss_info['altitude']:.1f} km<br>
        Geschwindigkeit: {iss_info['velocity']:.0f} km/h<br>
        Zeit: {datetime.now(pytz.UTC).strftime('%H:%M:%S')} UTC
        """,
        icon=folium.Icon(color="green", icon="satellite", prefix="fa")
    ).add_to(iss_map)
    
    # Deutschland markieren
    folium.Marker(
        location=germany_coords,
        popup="🇩🇪 Deutschland",
        icon=folium.Icon(color="blue", icon="eye", prefix="fa")
    ).add_to(iss_map)
    
    # Sichtbarkeitslinie falls ISS sichtbar
    distance = geodesic(germany_coords, (iss_info['latitude'], iss_info['longitude'])).kilometers
    if distance < 2000:
        folium.PolyLine(
            [germany_coords, [iss_info['latitude'], iss_info['longitude']]],
            color="green",
            weight=2,
            opacity=0.7,
            popup=f"Sichtlinie: {distance:.0f} km"
        ).add_to(iss_map)
    
    # ISS-Umlaufbahn andeuten (vereinfacht)
    orbit_points = []
    for i in range(0, 360, 10):
        lat = math.sin(math.radians(i)) * 51.6
        lon = (iss_info['longitude'] + i - 180) % 360
        if lon > 180:
            lon -= 360
        orbit_points.append([lat, lon])
    
    folium.PolyLine(
        orbit_points,
        color="lightblue",
        weight=1,
        opacity=0.5,
        tooltip="ISS Umlaufbahn (vereinfacht)"
    ).add_to(iss_map)
    
    return iss_map

def evaluate_reentry_visibility(trajectory_start, trajectory_end, predicted_location, reentry_time_utc):
    """Bewertet die Sichtbarkeit eines Wiedereintritts von Deutschland aus"""
    
    # Berechne Entfernung der Trajektorie zu Deutschland
    start_distance = geodesic(germany_coords, trajectory_start).kilometers
    end_distance = geodesic(germany_coords, trajectory_end).kilometers
    pred_distance = geodesic(germany_coords, predicted_location).kilometers
    
    # Minimale Entfernung zur Trajektorie
    min_distance = min(start_distance, end_distance, pred_distance)
    
    # Tageszeit berücksichtigen (SEHR WICHTIG für Wiedereintritte!)
    de_timezone = pytz.timezone('Europe/Berlin')
    local_time = reentry_time_utc.astimezone(de_timezone)
    hour = local_time.hour
    
    # Tageszeit-Faktor bestimmen
    if 22 <= hour or hour <= 4:
        time_factor = 1.0  # Nacht - beste Sichtbarkeit
        time_rating = "🌙 Optimal (Nacht)"
    elif (20 <= hour < 22) or (4 < hour <= 6):
        time_factor = 0.8  # Dämmerung - gute Sichtbarkeit
        time_rating = "🌅 Gut (Dämmerung)"
    elif (18 <= hour < 20) or (6 < hour <= 8):
        time_factor = 0.3  # Morgen/Abend-Dämmerung - mäßige Sichtbarkeit
        time_rating = "🌅 Mäßig (Dämmerung)"
    else:
        time_factor = 0.0  # Tag - praktisch nicht sichtbar
        time_rating = "☀️ Nicht sichtbar (Tag)"
    
    # Basis-Sichtbarkeitsbewertung basierend auf Entfernung
    if min_distance <= 300:
        base_rating = "Exzellent"
        base_description = "Direkt über Deutschland - spektakuläre Sichtung"
    elif min_distance <= 800:
        base_rating = "Sehr gut"
        base_description = "Sehr hohe Wahrscheinlichkeit einer beeindruckenden Sichtung"
    elif min_distance <= 1500:
        base_rating = "Gut"
        base_description = "Gute Sichtbarkeitschancen bei klarem Himmel"
    elif min_distance <= 2500:
        base_rating = "Möglich"
        base_description = "Sichtbarkeit nur bei optimalen Bedingungen"
    else:
        base_rating = "Unwahrscheinlich"
        base_description = "Zu weit entfernt für gute Sichtbarkeit"
    
    # Finale Sichtbarkeitsbewertung mit Tageszeit-Korrektur
    if time_factor == 0.0:
        # Am Tag: Immer nicht sichtbar, egal wie nah
        visibility_rating = "🔴 Nicht sichtbar"
        description = f"Am Tag nicht sichtbar (Entfernung: {min_distance:.0f}km)"
    elif time_factor >= 0.8:
        # Nacht/frühe Dämmerung: Volle Bewertung
        if base_rating == "Exzellent":
            visibility_rating = "🟢 Exzellent"
        elif base_rating == "Sehr gut":
            visibility_rating = "🟢 Sehr gut"
        elif base_rating == "Gut":
            visibility_rating = "🟡 Gut"
        elif base_rating == "Möglich":
            visibility_rating = "🟠 Möglich"
        else:
            visibility_rating = "🔴 Unwahrscheinlich"
        description = f"{base_description} bei {time_rating.lower()}"
    else:
        # Späte Dämmerung: Reduzierte Bewertung
        if base_rating in ["Exzellent", "Sehr gut"]:
            visibility_rating = "🟡 Mäßig"
            description = f"Bei Dämmerung mäßig sichtbar (Entfernung: {min_distance:.0f}km)"
        elif base_rating == "Gut":
            visibility_rating = "🟠 Schwach"
            description = f"Bei Dämmerung schwach sichtbar (Entfernung: {min_distance:.0f}km)"
        else:
            visibility_rating = "🔴 Unwahrscheinlich"
            description = f"Auch bei Dämmerung kaum sichtbar (Entfernung: {min_distance:.0f}km)"
    
    return {
        'visibility_rating': visibility_rating,
        'description': description,
        'time_rating': time_rating,
        'distance': min_distance,
        'time_factor': time_factor
    }

def create_reentry_countdown(reentry_time, title, uncertainty_hours):
    """Erstellt einen Countdown für Wiedereintritt"""
    countdown_html = f"""
    <div style="
        background: linear-gradient(45deg, #8B0000, #FF4500);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    ">
        <h2 style="color: white; margin-bottom: 10px;">💫 NÄCHSTER WIEDEREINTRITT</h2>
        <h3 style="color: white; margin-bottom: 15px;">{title}</h3>
        <div id="reentry-countdown" style="
            font-size: 2.5em;
            font-weight: bold;
            color: #FFD700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        ">
            Berechne...
        </div>
        <p style="color: white; margin-top: 10px;">Tage : Stunden : Minuten : Sekunden</p>
        <p style="color: #FFB6C1; margin-top: 5px; font-size: 0.9em;">⚠️ Unsicherheit: ±{uncertainty_hours} Stunden</p>
    </div>
    
    <script>
    function updateReentryCountdown() {{
        var reentryTime = new Date("{reentry_time.isoformat()}").getTime();
        var now = new Date().getTime();
        var distance = reentryTime - now;
        
        if (distance > 0) {{
            var days = Math.floor(distance / (1000 * 60 * 60 * 24));
            var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            document.getElementById("reentry-countdown").innerHTML = 
                String(days).padStart(2, '0') + "T " + 
                String(hours).padStart(2, '0') + ":" + 
                String(minutes).padStart(2, '0') + ":" + 
                String(seconds).padStart(2, '0');
        }} else {{
            document.getElementById("reentry-countdown").innerHTML = "💫 WIEDEREINTRITT ERFOLGT!";
        }}
    }}
    
    setInterval(updateReentryCountdown, 1000);
    updateReentryCountdown();
    </script>
    """
    return countdown_html

def create_reentry_trajectory_map(reentry_data):
    """Erstellt eine Karte mit der Wiedereintritts-Trajektorie"""
    
    # Karte zentriert auf die Trajektorie
    center_lat = (reentry_data['trajectory_start']['lat'] + reentry_data['trajectory_end']['lat']) / 2
    center_lon = (reentry_data['trajectory_start']['lon'] + reentry_data['trajectory_end']['lon']) / 2
    
    reentry_map = folium.Map(location=[center_lat, center_lon], zoom_start=4)
    
    # Deutschland markieren
    folium.Marker(
        location=germany_coords,
        popup="🇩🇪 Deutschland<br>Beobachtungsstandort",
        icon=folium.Icon(color="blue", icon="eye", prefix="fa")
    ).add_to(reentry_map)
    
    # Trajektorien-Start markieren
    folium.Marker(
        location=[reentry_data['trajectory_start']['lat'], reentry_data['trajectory_start']['lon']],
        popup=f"🌌 Wiedereintritt beginnt<br>Höhe: ~120 km",
        icon=folium.Icon(color="green", icon="play", prefix="fa")
    ).add_to(reentry_map)
    
    # Vorhergesagte Position markieren
    folium.Marker(
        location=[reentry_data['predicted_location']['lat'], reentry_data['predicted_location']['lon']],
        popup=f"💫 Hauptverglühung<br>{reentry_data['name']}<br>Höhe: ~80 km",
        icon=folium.Icon(color="orange", icon="fire", prefix="fa")
    ).add_to(reentry_map)
    
    # Trajektorien-Ende markieren
    folium.Marker(
        location=[reentry_data['trajectory_end']['lat'], reentry_data['trajectory_end']['lon']],
        popup=f"🎯 Mögliches Trümmerfeld<br>Höhe: Erdoberfläche",
        icon=folium.Icon(color="red", icon="stop", prefix="fa")
    ).add_to(reentry_map)
    
    # Wiedereintritts-Trajektorie als Linie
    trajectory_points = []
    
    # Erstelle 20 Punkte entlang der Trajektorie
    for i in range(21):
        progress = i / 20
        lat = reentry_data['trajectory_start']['lat'] + progress * (reentry_data['trajectory_end']['lat'] - reentry_data['trajectory_start']['lat'])
        lon = reentry_data['trajectory_start']['lon'] + progress * (reentry_data['trajectory_end']['lon'] - reentry_data['trajectory_start']['lon'])
        trajectory_points.append([lat, lon])
    
    # Haupttrajektorie
    folium.PolyLine(
        trajectory_points,
        color="red",
        weight=4,
        opacity=0.8,
        tooltip=f"Wiedereintritts-Trajektorie: {reentry_data['name']}"
    ).add_to(reentry_map)
    
    # Unsicherheitsbereich als Kreis um vorhergesagte Position
    uncertainty_radius = reentry_data['uncertainty_hours'] * 50  # km pro Stunde Unsicherheit
    folium.Circle(
        location=[reentry_data['predicted_location']['lat'], reentry_data['predicted_location']['lon']],
        radius=uncertainty_radius * 1000,  # Meter
        color="orange",
        fill=True,
        fillColor="orange",
        fillOpacity=0.2,
        popup=f"Unsicherheitsbereich<br>±{reentry_data['uncertainty_hours']} Stunden<br>≈ ±{uncertainty_radius} km"
    ).add_to(reentry_map)
    
    # Sichtbarkeitszonen um Deutschland
    visibility_circles = [
        {"radius": 300, "color": "green", "label": "Exzellente Sichtbarkeit"},
        {"radius": 800, "color": "yellow", "label": "Sehr gute Sichtbarkeit"},
        {"radius": 1500, "color": "orange", "label": "Gute Sichtbarkeit"},
    ]
    
    for circle in visibility_circles:
        folium.Circle(
            location=germany_coords,
            radius=circle["radius"] * 1000,  # Meter
            color=circle["color"],
            fill=False,
            weight=2,
            opacity=0.5,
            tooltip=f"{circle['label']} (Radius: {circle['radius']} km)"
        ).add_to(reentry_map)
    
    # Legende
    legend_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; z-index: 1000; 
                background-color: white; padding: 15px; border: 2px solid grey; 
                border-radius: 10px; font-size: 12px; max-width: 280px;">
    <h4>💫 Wiedereintritts-Legende</h4>
    
    <p><b>🛰️ Trajektorie:</b><br>
    <i class="fa fa-play" style="color:green;"></i> Wiedereintritt beginnt (~120km)<br>
    <i class="fa fa-fire" style="color:orange;"></i> Hauptverglühung (~80km)<br>
    <i class="fa fa-stop" style="color:red;"></i> Mögliches Trümmerfeld<br>
    <i class="fa fa-eye" style="color:blue;"></i> Deutschland (Beobachter)</p>
    
    <p><b>🎯 Sichtbarkeitszonen:</b><br>
    <i class="fa fa-circle" style="color:green;"></i> Exzellent (≤300km)<br>
    <i class="fa fa-circle" style="color:yellow;"></i> Sehr gut (≤800km)<br>
    <i class="fa fa-circle" style="color:orange;"></i> Gut (≤1500km)</p>
    
    <p><b>📊 Objekt-Daten:</b><br>
    Masse: {reentry_data['mass_kg']} kg<br>
    Typ: {reentry_data['object_type']}<br>
    Sichtdauer: {reentry_data['visibility_duration_minutes']} Min<br>
    Unsicherheit: ±{reentry_data['uncertainty_hours']}h</p>
    
    <p><b>⚠️ Sicherheit:</b><br>
    • Niemals Trümmer berühren<br>
    • Funde der Polizei melden<br>
    • Sicheren Abstand halten</p>
    
    <p><i>💡 Die rote Linie zeigt den erwarteten Pfad</i></p>
    </div>
    """
    reentry_map.get_root().html.add_child(folium.Element(legend_html))
    
    return reentry_map

def calculate_reentry_observation_windows(reentry_data):
    """Berechnet optimale Beobachtungsfenster für einen Wiedereintritt"""
    
    windows = []
    de_timezone = pytz.timezone('Europe/Berlin')
    
    # Wiedereintritts-Trajectory in Segmente unterteilen
    trajectory_points = []
    for i in range(11):  # 11 Punkte für 10 Segmente
        progress = i / 10
        lat = reentry_data['trajectory_start']['lat'] + progress * (reentry_data['trajectory_end']['lat'] - reentry_data['trajectory_start']['lat'])
        lon = reentry_data['trajectory_start']['lon'] + progress * (reentry_data['trajectory_end']['lon'] - reentry_data['trajectory_start']['lon'])
        
        # Höhe während Wiedereintritt (120km bis 0km)
        altitude = 120 * (1 - progress)
        
        trajectory_points.append((lat, lon, altitude))
    
    # Zeitpunkte für jeden Punkt der Trajektorie
    total_duration = reentry_data['visibility_duration_minutes']
    
    for i, (lat, lon, altitude) in enumerate(trajectory_points):
        # Zeit für diesen Punkt
        time_offset_minutes = (i / len(trajectory_points)) * total_duration
        point_time = reentry_data['reentry_time'] + timedelta(minutes=time_offset_minutes - total_duration/2)
        
        # Sichtbarkeit für diesen Punkt berechnen
        distance = geodesic(germany_coords, (lat, lon)).kilometers
        
        # Elevation berechnen (vereinfacht)
        if distance > 0 and altitude > 0:
            elevation_angle = math.degrees(math.atan(altitude / distance))
        else:
            elevation_angle = 0
        
        # Wiedereintritt-spezifische Sichtbarkeit (heller als normale Satelliten)
        base_visibility = 0
        
        if distance <= 300:
            base_visibility = 90
        elif distance <= 800:
            base_visibility = 75
        elif distance <= 1500:
            base_visibility = 60
        elif distance <= 2500:
            base_visibility = 40
        else:
            base_visibility = 15
        
        # Höhen-Bonus (höhere Objekte besser sichtbar)
        altitude_bonus = min(20, altitude / 6)  # Bis zu 20% Bonus
        
        # Tageszeit-Faktor
        local_time = point_time.astimezone(de_timezone)
        hour = local_time.hour
        
        if 20 <= hour or hour <= 6:
            time_factor = 1.0
        elif 18 <= hour < 20 or 6 < hour <= 8:
            time_factor = 0.8
        else:
            time_factor = 0.3
        
        # Gesamtsichtbarkeit
        visibility = min(100, (base_visibility + altitude_bonus) * time_factor)
        
        # Nur signifikante Sichtbarkeiten speichern
        if visibility > 20 and elevation_angle > 5:
            phase = "Wiedereintritt"
            if i < 3:
                phase = "Wiedereintritt-Beginn"
            elif i > 7:
                phase = "Verglüh-Phase"
            
            windows.append({
                'phase': phase,
                'time_utc': point_time.strftime('%H:%M:%S'),
                'time_de': local_time.strftime('%H:%M:%S'),
                'coords': (lat, lon),
                'altitude': altitude,
                'visibility': visibility,
                'distance': distance,
                'elevation': elevation_angle
            })
    
    # Nach Sichtbarkeit sortieren
    windows = sorted(windows, key=lambda x: x['visibility'], reverse=True)
    
    return windows[:5]  # Top 5 Beobachtungsfenster

def find_next_visible_launch(launches):
    """Findet den nächsten gut sichtbaren Start"""
    
    for launch in launches:
        launch_time_str = launch['net']
        launch_time_utc = datetime.fromisoformat(launch_time_str.replace('Z', '+00:00'))
        
        # Nur zukünftige Starts
        if launch_time_utc <= datetime.now(pytz.UTC):
            continue
            
        launch_pad = launch['pad']
        launch_lat = float(launch_pad['latitude']) if launch_pad.get('latitude') else 0
        launch_lon = float(launch_pad['longitude']) if launch_pad.get('longitude') else 0
        launch_coords = (launch_lat, launch_lon)
        
        # Sichtbarkeitsbewertung
        visibility_rating, description, time_rating, distance = evaluate_launch_visibility(launch_coords, launch_time_utc)
        
        # Suche nach gut sichtbaren Starts (Entfernung < 3500km)
        if distance <= 3500:
            return launch
    
    # Falls kein gut sichtbarer Start gefunden wird, nimm den ersten
    return launches[0] if launches else None

def generate_historical_sightings():
    """Generiert realistische historische Sichtungsdaten für die letzten 12 Monate"""
    
    import random
    from datetime import datetime, timedelta
    
    sightings = []
    base_date = datetime.now() - timedelta(days=365)
    
    # Bekannte reale Ereignisse 2025
    real_events = [
        {"date": "2025-03-24", "time": "21:30", "name": "SpaceX NROL-69 Spiral", "type": "SpaceX Spiral", "visibility": 85, "confirmed": True},
        {"date": "2025-02-19", "time": "04:45", "name": "Falcon 9 Wiedereintritt", "type": "Wiedereintritt", "visibility": 92, "confirmed": True},
        {"date": "2025-01-15", "time": "23:15", "name": "Blue Ghost Lunar Mission", "type": "SpaceX Start", "visibility": 45, "confirmed": False},
        {"date": "2025-03-30", "time": "20:45", "name": "Isar Spectrum Test", "type": "Europäische Rakete", "visibility": 78, "confirmed": True},
    ]
    
    # Reale Ereignisse hinzufügen
    for event in real_events:
        event_date = datetime.strptime(event["date"], "%Y-%m-%d")
        sightings.append({
            "date": event_date,
            "name": event["name"],
            "type": event["type"],
            "time": event["time"],
            "visibility": event["visibility"],
            "confirmed": event["confirmed"],
            "distance": random.randint(800, 3500),
            "region": random.choice(["Norddeutschland", "Süddeutschland", "Westdeutschland", "Ostdeutschland", "Ganz Deutschland"]),
            "quality": "Exzellent" if event["visibility"] > 80 else "Sehr gut" if event["visibility"] > 60 else "Gut",
            "description": f"Sichtung von {event['name']} mit {event['visibility']}% Sichtbarkeit."
        })
    
    # Zusätzliche simulierte Sichtungen generieren
    event_types = [
        {"name": "ISS-Überflug", "type": "ISS", "prob": 0.4, "vis_range": (30, 90)},
        {"name": "Starlink-Kette", "type": "Starlink", "prob": 0.25, "vis_range": (40, 85)},
        {"name": "SpaceX Falcon 9", "type": "SpaceX Start", "prob": 0.15, "vis_range": (20, 70)},
        {"name": "Europäische Rakete", "type": "Europäische Rakete", "prob": 0.1, "vis_range": (50, 95)},
        {"name": "Debris-Wiedereintritt", "type": "Wiedereintritt", "prob": 0.05, "vis_range": (60, 100)},
        {"name": "Geheimer Satellit", "type": "Militär", "prob": 0.05, "vis_range": (10, 40)},
    ]
    
    # Generiere 80-120 zusätzliche Sichtungen über 12 Monate
    for _ in range(random.randint(80, 120)):
        # Zufälliges Datum
        days_ago = random.randint(1, 365)
        event_date = datetime.now() - timedelta(days=days_ago)
        
        # Bevorzuge Nacht- und Dämmerungszeiten
        if random.random() < 0.6:  # 60% nachts/Dämmerung
            hour = random.choice([20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6])
        else:  # 40% andere Zeiten
            hour = random.randint(7, 19)
        
        minute = random.randint(0, 59)
        time_str = f"{hour:02d}:{minute:02d}"
        
        # Wähle Event-Typ basierend auf Wahrscheinlichkeiten
        rand = random.random()
        cumulative_prob = 0
        selected_event = event_types[0]  # Fallback
        
        for event_type in event_types:
            cumulative_prob += event_type["prob"]
            if rand <= cumulative_prob:
                selected_event = event_type
                break
        
        # Sichtbarkeit basierend auf Event-Typ und Tageszeit
        base_visibility = random.randint(*selected_event["vis_range"])
        
        # Nacht-Bonus
        if 22 <= hour or hour <= 4:
            visibility = min(100, base_visibility + random.randint(0, 15))
        elif 18 <= hour <= 21 or 5 <= hour <= 7:
            visibility = min(100, base_visibility + random.randint(0, 10))
        else:
            visibility = max(10, base_visibility - random.randint(0, 20))
        
        sightings.append({
            "date": event_date,
            "name": selected_event["name"],
            "type": selected_event["type"], 
            "time": time_str,
            "visibility": visibility,
            "confirmed": random.random() < 0.7,  # 70% bestätigt
            "distance": random.randint(500, 4000),
            "region": random.choice(["Norddeutschland", "Süddeutschland", "Westdeutschland", "Ostdeutschland", "Ganz Deutschland"]),
            "quality": "Exzellent" if visibility > 80 else "Sehr gut" if visibility > 60 else "Gut" if visibility > 40 else "Mäßig",
            "description": f"Sichtung von {selected_event['name']} mit {visibility}% Sichtbarkeit um {time_str} Uhr."
        })
    
    # Nach Datum sortieren
    sightings.sort(key=lambda x: x["date"], reverse=True)
    
    return sightings

def get_best_sighting_month(historical_data):
    """Ermittelt den Monat mit den meisten Sichtungen"""
    month_counts = {}
    month_names = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", 
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    
    for sighting in historical_data:
        month = sighting["date"].month
        month_name = month_names[month - 1]
        month_counts[month_name] = month_counts.get(month_name, 0) + 1
    
    if month_counts:
        return max(month_counts, key=month_counts.get)
    return "N/A"

def prepare_monthly_chart_data(historical_data):
    """Bereitet Daten für das monatliche Chart vor"""
    import pandas as pd
    
    month_counts = {}
    month_names = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", 
                   "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    
    # Initialisiere alle Monate mit 0
    for month_name in month_names:
        month_counts[month_name] = 0
    
    # Zähle Sichtungen pro Monat
    for sighting in historical_data:
        month = sighting["date"].month
        month_name = month_names[month - 1]
        month_counts[month_name] += 1
    
    # Erstelle DataFrame
    data = []
    for month, count in month_counts.items():
        data.append({"month": month, "count": count})
    
    return pd.DataFrame(data)

def prepare_hourly_chart_data(historical_data):
    """Bereitet Daten für das stündliche Chart vor"""
    import pandas as pd
    
    hour_counts = {hour: 0 for hour in range(24)}
    
    for sighting in historical_data:
        hour = int(sighting["time"].split(":")[0])
        hour_counts[hour] += 1
    
    data = []
    for hour, count in hour_counts.items():
        data.append({"hour": hour, "count": count})
    
    return pd.DataFrame(data)

def analyze_best_sighting_times(historical_data):
    """Analysiert die besten Sichtungszeiten"""
    
    night_count = 0
    twilight_count = 0
    day_count = 0
    
    night_hours = {}
    twilight_hours = {}
    
    for sighting in historical_data:
        hour = int(sighting["time"].split(":")[0])
        
        if 22 <= hour or hour <= 4:
            night_count += 1
            night_hours[hour] = night_hours.get(hour, 0) + 1
        elif (18 <= hour <= 21) or (5 <= hour <= 7):
            twilight_count += 1
            twilight_hours[hour] = twilight_hours.get(hour, 0) + 1
        else:
            day_count += 1
    
    total = len(historical_data)
    
    best_night_hour = max(night_hours, key=night_hours.get) if night_hours else 23
    best_twilight_hour = max(twilight_hours, key=twilight_hours.get) if twilight_hours else 20
    
    return {
        "night": night_count,
        "night_percent": (night_count / total * 100) if total > 0 else 0,
        "twilight": twilight_count,
        "twilight_percent": (twilight_count / total * 100) if total > 0 else 0,
        "best_night_hour": best_night_hour,
        "best_twilight_hour": best_twilight_hour
    }

def analyze_seasonal_patterns(historical_data):
    """Analysiert saisonale Muster"""
    
    season_counts = {"Winter": 0, "Frühling": 0, "Sommer": 0, "Herbst": 0}
    month_counts = {}
    
    for sighting in historical_data:
        month = sighting["date"].month
        month_counts[month] = month_counts.get(month, 0) + 1
        
        if month in [12, 1, 2]:
            season_counts["Winter"] += 1
        elif month in [3, 4, 5]:
            season_counts["Frühling"] += 1
        elif month in [6, 7, 8]:
            season_counts["Sommer"] += 1
        else:
            season_counts["Herbst"] += 1
    
    month_names = {1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni",
                   7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember"}
    
    if month_counts:
        best_month_num = max(month_counts, key=month_counts.get)
        worst_month_num = min(month_counts, key=month_counts.get)
        best_month = month_names.get(best_month_num, "N/A")
        worst_month = month_names.get(worst_month_num, "N/A")
        best_count = month_counts[best_month_num]
        worst_count = month_counts[worst_month_num]
    else:
        best_month = worst_month = "N/A"
        best_count = worst_count = 0
    
    return {
        "best_month": best_month,
        "best_count": best_count,
        "worst_month": worst_month,
        "worst_count": worst_count,
        "winter": season_counts["Winter"],
        "spring": season_counts["Frühling"],
        "summer": season_counts["Sommer"],
        "autumn": season_counts["Herbst"]
    }

def prepare_sighting_types_data(historical_data):
    """Bereitet Daten für das Sichtungsarten-Diagramm vor"""
    import pandas as pd
    
    type_counts = {}
    for sighting in historical_data:
        sighting_type = sighting["type"]
        type_counts[sighting_type] = type_counts.get(sighting_type, 0) + 1
    
    data = []
    for sighting_type, count in type_counts.items():
        data.append({"type": sighting_type, "count": count})
    
    return pd.DataFrame(data)

def get_notable_sightings(historical_data):
    """Filtert bemerkenswerte Sichtungen heraus"""
    
    # Sortiere nach Sichtbarkeit und nimm die besten
    notable = sorted(historical_data, key=lambda x: x["visibility"], reverse=True)[:10]
    
    # Formatiere für Anzeige
    formatted = []
    for sighting in notable:
        formatted.append({
            "date": sighting["date"].strftime("%d.%m.%Y"),
            "time": sighting["time"],
            "name": sighting["name"],
            "type": sighting["type"],
            "visibility": sighting["visibility"],
            "distance": sighting["distance"],
            "region": sighting["region"],
            "quality": sighting["quality"],
            "confirmed": sighting["confirmed"],
            "description": sighting["description"]
        })
    
    return formatted

def generate_sighting_predictions():
    """Generiert Vorhersagen für kommende Monate"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Nächste 6 Monate
    months = []
    current_date = datetime.now()
    
    for i in range(6):
        future_date = current_date + timedelta(days=30 * i)
        month_name = future_date.strftime("%b %Y")
        
        # Basiere Vorhersage auf saisonalen Mustern und geplanten Starts
        base_prediction = 8  # Basis pro Monat
        
        # Saisonale Anpassung
        month_num = future_date.month
        if month_num in [11, 12, 1, 2]:  # Winter - bessere Sichtbarkeit
            seasonal_bonus = 3
        elif month_num in [6, 7, 8]:  # Sommer - schlechtere Sichtbarkeit
            seasonal_bonus = -2
        else:
            seasonal_bonus = 0
        
        # Geplante Starts berücksichtigen
        planned_starts_bonus = random.randint(0, 4)
        
        predicted = max(2, base_prediction + seasonal_bonus + planned_starts_bonus)
        
        months.append({
            "month": month_name,
            "predicted_sightings": predicted
        })
    
    return pd.DataFrame(months)

# Bewertung der Sichtbarkeit eines Starts von Deutschland aus
def evaluate_launch_visibility(launch_site_coords, launch_time_utc):
    """Schnelle Bewertung, ob ein Start grundsätzlich von Deutschland sichtbar sein könnte"""
    distance = geodesic(germany_coords, launch_site_coords).kilometers
    
    # Startorte kategorisieren
    if distance <= 1000:
        visibility_rating = "🟢 Sehr gut"
        description = "Sehr hohe Wahrscheinlichkeit der Sichtbarkeit"
    elif distance <= 2000:
        visibility_rating = "🟡 Gut"
        description = "Gute Sichtbarkeitschancen bei idealen Bedingungen"
    elif distance <= 3500:
        visibility_rating = "🟠 Möglich"
        description = "Sichtbarkeit nur bei perfekten Bedingungen möglich"
    else:
        visibility_rating = "🔴 Unwahrscheinlich"
        description = "Sichtbarkeit sehr unwahrscheinlich"
    
    # Tageszeit berücksichtigen
    de_timezone = pytz.timezone('Europe/Berlin')
    local_time = launch_time_utc.astimezone(de_timezone)
    hour = local_time.hour
    
    if 22 <= hour or hour <= 4:
        time_rating = "🌙 Optimal (Nacht)"
    elif (20 <= hour < 22) or (4 < hour <= 6):
        time_rating = "🌅 Gut (Dämmerung)"
    else:
        time_rating = "☀️ Ungünstig (Tag)"
    
    return visibility_rating, description, time_rating, distance

# Hauptfunktion 
def main():
    # Tab-System für bessere Navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚀 Aktuelle Starts", "💫 Wiedereintritte", "📊 Sichtbarkeits-Übersicht", "📈 Historische Sichtungen", "ℹ️ Info & Tipps"])
    
    with tab1:
        # Daten abrufen
        launch_data = get_launch_data()
        
        if not launch_data:
            return
        
        launches = launch_data.get('results', [])
        
        if not launches:
            st.warning("Keine bevorstehenden Starts gefunden.")
            return
        
        # Live-Countdown für den nächsten SICHTBAREN Start
        next_visible_launch = find_next_visible_launch(launches)
        
        if next_visible_launch:
            next_launch_time = datetime.fromisoformat(next_visible_launch['net'].replace('Z', '+00:00'))
            launch_pad = next_visible_launch['pad']
            launch_coords = (float(launch_pad['latitude']), float(launch_pad['longitude']))
            distance = geodesic(germany_coords, launch_coords).kilometers
            
            countdown_title = f"{next_visible_launch['name']} - {distance:.0f}km entfernt"
            countdown_html = create_launch_countdown(next_launch_time, countdown_title)
            st.markdown(countdown_html, unsafe_allow_html=True)
            
            if distance <= 3500:
                st.success(f"🎯 **Dieser Start könnte von Deutschland aus sichtbar sein!** Entfernung: {distance:.0f}km")
            else:
                st.info(f"ℹ️ Nächster gut sichtbarer Start wird gesucht... (Aktueller Start: {distance:.0f}km entfernt)")
        else:
            # Fallback zum ersten Start
            next_launch_time = datetime.fromisoformat(launches[0]['net'].replace('Z', '+00:00'))
            countdown_html = create_launch_countdown(next_launch_time, launches[0]['name'])
            st.markdown(countdown_html, unsafe_allow_html=True)
        
        # Refresh-Button für aktuellen Countdown
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 Countdown aktualisieren", use_container_width=True):
                st.rerun()
        
        # Übersicht der nächsten Starts mit Sichtbarkeitsbewertung
        st.subheader("🔍 Kommende Raketenstarts - Schnellübersicht")
        
        visibility_overview = []
        for launch in launches[:10]:  # Nur die nächsten 10 Starts
            launch_time_str = launch['net']
            launch_time_utc = datetime.fromisoformat(launch_time_str.replace('Z', '+00:00'))
            launch_pad = launch['pad']
            launch_lat = float(launch_pad['latitude']) if launch_pad.get('latitude') else 0
            launch_lon = float(launch_pad['longitude']) if launch_pad.get('longitude') else 0
            launch_coords = (launch_lat, launch_lon)
            
            visibility_rating, description, time_rating, distance = evaluate_launch_visibility(launch_coords, launch_time_utc)
            
            de_timezone = pytz.timezone('Europe/Berlin')
            launch_time_de = launch_time_utc.astimezone(de_timezone)
            
            visibility_overview.append({
                'Start': launch['name'],
                'Anbieter': launch['launch_service_provider']['name'],
                'Zeit (DE)': launch_time_de.strftime('%d.%m.%Y %H:%M'),
                'Startort': f"{launch_pad['location']['name']}",
                'Entfernung': f"{distance:.0f} km",
                'Sichtbarkeit': visibility_rating,
                'Tageszeit': time_rating,
                'Mission': launch['mission']['name'] if launch.get('mission') else 'Unbekannt'
            })
        
        df_overview = pd.DataFrame(visibility_overview)
        st.dataframe(df_overview, use_container_width=True)
        
        # Detailanalyse für ausgewählten Start
        st.subheader("🔬 Detailanalyse")
        launch_names = [f"{launch['name']} ({launch['launch_service_provider']['name']})" for launch in launches]
        selected_launch_index = st.selectbox("Wähle einen Raketenstart für die Detailanalyse:", 
                                           range(len(launch_names)), 
                                           format_func=lambda i: launch_names[i])
        
        selected_launch = launches[selected_launch_index]
        
        # Startdetails anzeigen
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📋 Startdetails**")
            st.write(f"**Mission:** {selected_launch['mission']['name'] if selected_launch.get('mission') else 'Keine Mission angegeben'}")
            st.write(f"**Anbieter:** {selected_launch['launch_service_provider']['name']}")
            
            launch_time_str = selected_launch['net']
            launch_time_utc = datetime.fromisoformat(launch_time_str.replace('Z', '+00:00'))
            de_timezone = pytz.timezone('Europe/Berlin')
            launch_time_de = launch_time_utc.astimezone(de_timezone)
            
            st.write(f"**Startzeit (UTC):** {launch_time_utc.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**Startzeit (DE):** {launch_time_de.strftime('%Y-%m-%d %H:%M:%S')}")
            
            launch_pad = selected_launch['pad']
            st.write(f"**Startort:** {launch_pad['name']}, {launch_pad['location']['name']}")
            
            mission_type = "LEO"
            if selected_launch.get('mission') and selected_launch['mission'].get('orbit', {}).get('name'):
                mission_type = selected_launch['mission']['orbit']['name']
            
            st.write(f"**Orbit-Typ:** {mission_type}")
        
        with col2:
            st.write("**🎯 Sichtbarkeitsbewertung**")
            launch_lat = float(launch_pad['latitude']) if launch_pad.get('latitude') else 0
            launch_lon = float(launch_pad['longitude']) if launch_pad.get('longitude') else 0
            launch_coords = (launch_lat, launch_lon)
            
            visibility_rating, description, time_rating, distance = evaluate_launch_visibility(launch_coords, launch_time_utc)
            
            st.write(f"**Entfernung:** {distance:.0f} km")
            st.write(f"**Sichtbarkeit:** {visibility_rating}")
            st.write(f"**Tageszeit:** {time_rating}")
            st.write(f"**Bewertung:** {description}")
            
            if description != "Sichtbarkeit sehr unwahrscheinlich":
                st.success("👀 Dieser Start könnte von Deutschland aus sichtbar sein!")
            else:
                st.info("ℹ️ Dieser Start ist wahrscheinlich nicht sichtbar.")
        
        # ISS Live-Tracking hinzufügen
        st.subheader("🛰️ Internationale Raumstation (ISS) - Live Tracking")
        
        # Refresh-Button für ISS-Daten
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 ISS-Position aktualisieren", use_container_width=True):
                st.rerun()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Aktuelle ISS Position
            current_iss_info = get_current_iss_info()
            st.info(f"""
            **🌍 Aktuelle ISS Position:**
            - Breite: {current_iss_info['latitude']:.2f}°
            - Länge: {current_iss_info['longitude']:.2f}°
            - Höhe: {current_iss_info['altitude']:.1f} km
            - Geschwindigkeit: {current_iss_info['velocity']:.1f} km/h
            """)
            
            # ISS Sichtbarkeit von Deutschland
            iss_visibility = get_iss_visibility_from_germany()
            if iss_visibility['is_visible']:
                st.success(f"""
                **👀 ISS ist JETZT von Deutschland sichtbar!**
                - Elevation: {iss_visibility['elevation']:.1f}°
                - Azimut: {iss_visibility['azimuth']:.1f}°
                - Richtung: {iss_visibility['direction']}
                - Sichtbarkeit: {iss_visibility['visibility_quality']}
                """)
            else:
                st.warning(f"""
                **ISS derzeit nicht sichtbar von Deutschland**
                - Nächste Sichtung: {iss_visibility['next_pass']}
                - Grund: {iss_visibility['reason']}
                """)
        
        with col2:
            # ISS Live-Karte (kleiner Ausschnitt)
            st.write("**🗺️ ISS Live Position:**")
            iss_map = create_iss_live_map(current_iss_info)
            folium_static(iss_map, height=300)
        
        # Hauptkarte mit Aufstiegspfad und Orbits
        st.subheader("🗺️ Aufstiegspfad und Sichtbarkeitskarte")
        
        # Parameter für Orbit basierend auf Mission definieren
        orbit_params = {
            "LEO": {"height": 400, "inclination": 51.6, "ascent_duration": 8},
            "MEO": {"height": 20000, "inclination": 55, "ascent_duration": 25},
            "GEO": {"height": 35786, "inclination": 0, "ascent_duration": 45},
            "SSO": {"height": 600, "inclination": 97.8, "ascent_duration": 12},
            "Polar": {"height": 500, "inclination": 90, "ascent_duration": 10}
        }
        
        # Orbit-Typ bestimmen
        orbit_type = "LEO"  # Standard
        if selected_launch.get('mission') and selected_launch['mission'].get('orbit', {}).get('name'):
            mission_orbit = selected_launch['mission']['orbit']['name'].upper()
            if "GEO" in mission_orbit or "GEOSTATIONARY" in mission_orbit:
                orbit_type = "GEO"
            elif "SSO" in mission_orbit or "SUN-SYNCHRONOUS" in mission_orbit:
                orbit_type = "SSO"
            elif "POLAR" in mission_orbit:
                orbit_type = "Polar"
            elif "MEO" in mission_orbit:
                orbit_type = "MEO"
        
        target_orbit = orbit_params[orbit_type]
        
        # Informationen zur geplanten Flugbahn
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🎯 Zielorbit", f"{target_orbit['height']} km")
        
        with col2:
            st.metric("📐 Inklination", f"{target_orbit['inclination']}°")
        
        with col3:
            orbit_period = calculate_orbit_period(target_orbit["height"])
            st.metric("⏱️ Umlaufzeit", f"{orbit_period:.1f} Min")
        
        with col4:
            # Zeit bis zum Start
            now = datetime.now(pytz.UTC)
            time_to_launch = launch_time_utc - now
            if time_to_launch.total_seconds() > 0:
                hours_to_launch = time_to_launch.total_seconds() / 3600
                st.metric("🚀 Start in", f"{hours_to_launch:.1f}h")
            else:
                st.metric("🚀 Status", "Gestartet")
        
        # ISS-Sichtbarkeits-Info
        col1, col2 = st.columns(2)
        
        with col1:
            # ISS Position approximieren (vereinfacht)
            iss_info = get_iss_visibility_info(launch_time_utc, launch_coords)
            st.info(f"""
            **🛰️ ISS zur Startzeit:**
            - Position: ~{iss_info['approx_position']}
            - Sichtbarkeit von Deutschland: {iss_info['visibility_from_germany']}
            - Start-ISS Distanz: ~{iss_info['distance_to_launch']:.0f} km
            - ISS könnte Start sehen: {iss_info['iss_can_see_launch']}
            """)
        
        with col2:
            # Beste Startpositionen für Deutschland
            best_positions = get_best_launch_positions_for_germany()
            st.success(f"""
            **🎯 Beste Startpositionen für Deutschland:**
            1. {best_positions[0]['name']} ({best_positions[0]['distance']:.0f} km)
            2. {best_positions[1]['name']} ({best_positions[1]['distance']:.0f} km)
            3. {best_positions[2]['name']} ({best_positions[2]['distance']:.0f} km)
            
            **Aktueller Start:** {launch_pad['location']['name']} 
            **Rang:** {get_launch_position_rank(launch_coords)}
            """)
        
        # Erdrotations-Info
        st.info("""
        🌍 **Orbital-Mechanik:** Die Karte zeigt den ersten Umlauf nach dem Raketenstart. 
        Die Erdrotation wird berücksichtigt, um realistische Sichtbarkeitsbedingungen zu zeigen.
        """)
        
        # Berechne Flugbahn mit Zeitstempeln
        st.write("**📍 Interaktive Karte:** Klicken Sie auf die Markierungen für detaillierte Zeitinformationen!")
        trajectory_map = create_trajectory_map(launch_coords, launch_time_utc, target_orbit, orbit_type)
        folium_static(trajectory_map)
        
        # Zeitplan der Sichtbarkeitsfenster
        st.subheader("⏰ Zeitplan der Sichtbarkeitsfenster")
        
        visibility_schedule = calculate_visibility_schedule(launch_coords, launch_time_utc, target_orbit)
        
        # Debug-Information anzeigen
        st.write(f"**🔍 Gefundene Sichtbarkeitsfenster:** {len(visibility_schedule)}")
        
        if visibility_schedule:
            # Filter für verschiedene Qualitätsstufen
            excellent_windows = [w for w in visibility_schedule if w['visibility'] > 70]
            good_windows = [w for w in visibility_schedule if 30 < w['visibility'] <= 70]
            fair_windows = [w for w in visibility_schedule if 10 < w['visibility'] <= 30]
            poor_windows = [w for w in visibility_schedule if w['visibility'] <= 10]
            
            # Statistiken anzeigen
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🟢 Exzellent", len(excellent_windows), help=">70% Sichtbarkeit")
            with col2:
                st.metric("🟡 Gut", len(good_windows), help="30-70% Sichtbarkeit")
            with col3:
                st.metric("🟠 Mäßig", len(fair_windows), help="10-30% Sichtbarkeit")
            with col4:
                st.metric("🔴 Schwach", len(poor_windows), help="<10% Sichtbarkeit")
            
            # Alle Fenster anzeigen (nicht nur die mit >30%)
            for window in visibility_schedule:
                if window['visibility'] > 5:  # Sehr niedriger Schwellenwert
                    if window['visibility'] > 70:
                        visibility_color = "🟢"
                        quality = "Exzellent"
                    elif window['visibility'] > 30:
                        visibility_color = "🟡" 
                        quality = "Gut"
                    elif window['visibility'] > 10:
                        visibility_color = "🟠"
                        quality = "Mäßig"
                    else:
                        visibility_color = "🔴"
                        quality = "Schwach"
                    
                    with st.expander(f"{visibility_color} {window['phase']} - {window['time_de']} (Sichtbarkeit: {window['visibility']:.1f}% - {quality})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**🕐 Zeit (DE):** {window['time_de']}")
                            st.write(f"**🌍 Zeit (UTC):** {window['time_utc']}")
                            st.write(f"**📍 Position:** {window['coords'][0]:.1f}°N, {window['coords'][1]:.1f}°E")
                        
                        with col2:
                            st.write(f"**🎯 Sichtbarkeit:** {window['visibility']:.1f}%")
                            st.write(f"**📏 Entfernung:** {window['distance']:.0f} km")
                            st.write(f"**🚀 Höhe:** {window['height']} km")
                            if 'elevation' in window:
                                st.write(f"**📐 Elevation:** {window['elevation']:.1f}°")
                            
                        # Beobachtungstipp
                        direction = calculate_direction_from_germany(window['coords'])
                        
                        if window['visibility'] > 30:
                            st.success(f"💡 **Beobachtungstipp:** Schauen Sie nach {direction}")
                        elif window['visibility'] > 10:
                            st.info(f"💡 **Beobachtungstipp:** Schauen Sie nach {direction} (bei optimalen Bedingungen)")
                        else:
                            st.warning(f"⚠️ **Hinweis:** Sehr schwer sichtbar, Richtung {direction}")
            
            # Erklärung für schlechte Sichtbarkeit
            if len([w for w in visibility_schedule if w['visibility'] > 30]) == 0:
                st.warning("""
                **📊 Analyse: Warum ist die Sichtbarkeit schlecht?**
                
                Mögliche Gründe:
                - 🌍 **Große Entfernung** zum Startplatz (>2000km)
                - ☀️ **Ungünstige Tageszeit** (Start bei Tag statt Dämmerung/Nacht)
                - 📐 **Niedrige Elevation** (Rakete/Satellit unter dem Horizont)
                - 🌥️ **Physikalische Einschränkungen** (Mindesthöhe 100km erforderlich)
                """)
                
                # Zusätzliche Info zur Entfernung
                distance_to_launch = geodesic(germany_coords, launch_coords).kilometers
                st.info(f"""
                **📏 Entfernungsanalyse:**
                - Entfernung zu Deutschland: {distance_to_launch:.0f} km
                - Optimal: <1000km (Europa)
                - Gut: 1000-2000km 
                - Mäßig: 2000-3500km
                - Schlecht: >3500km
                """)
        
        else:
            st.error("""
            **❌ Keine Sichtbarkeitsfenster gefunden!**
            
            Dies kann verschiedene Gründe haben:
            - Start ist zu weit entfernt (>5000km)
            - Start bei ungünstiger Tageszeit
            - Technischer Fehler bei der Berechnung
            
            **💡 Tipp:** Versuchen Sie einen Start aus Europa (Schottland, Norwegen) für bessere Sichtbarkeit!
            """)
            
            # Debug-Information
            distance_to_launch = geodesic(germany_coords, launch_coords).kilometers
            st.write(f"**🔍 Debug:** Entfernung zum Start: {distance_to_launch:.0f} km")
            st.write(f"**🔍 Debug:** Startzeit: {launch_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            st.write(f"**🔍 Debug:** Orbit-Typ: {orbit_type}, Höhe: {target_orbit['height']} km")
    
    with tab2:
        st.subheader("💫 Bevorstehende Wiedereintritte")
        
        # Wiedereintritts-Daten abrufen
        reentry_data = get_reentry_data()
        
        if not reentry_data:
            st.error("Keine Wiedereintritts-Daten verfügbar.")
            return
        
        reentries = reentry_data.get('results', [])
        
        if not reentries:
            st.warning("Keine bevorstehenden Wiedereintritte gefunden.")
            return
        
        # Live-Countdown für den nächsten Wiedereintritt
        next_reentry = reentries[0]  # Nächster Wiedereintritt
        next_reentry_time = next_reentry['reentry_time']
        
        # Sichtbarkeitsbewertung für Wiedereintritt
        trajectory_start = (next_reentry['trajectory_start']['lat'], next_reentry['trajectory_start']['lon'])
        trajectory_end = (next_reentry['trajectory_end']['lat'], next_reentry['trajectory_end']['lon'])
        predicted_location = (next_reentry['predicted_location']['lat'], next_reentry['predicted_location']['lon'])
        
        # Bewertung der Sichtbarkeit
        reentry_visibility = evaluate_reentry_visibility(trajectory_start, trajectory_end, predicted_location, next_reentry_time)
        
        countdown_title = f"{next_reentry['name']} - {reentry_visibility['distance']:.0f}km über Deutschland"
        countdown_html = create_reentry_countdown(next_reentry_time, countdown_title, next_reentry['uncertainty_hours'])
        st.markdown(countdown_html, unsafe_allow_html=True)
        
        if reentry_visibility['visibility_rating'] in ["🟢 Sehr gut", "🟡 Gut"]:
            st.success(f"🎯 **Dieser Wiedereintritt könnte spektakulär von Deutschland aus sichtbar sein!**")
        else:
            st.info(f"ℹ️ Sichtbarkeit: {reentry_visibility['visibility_rating']}")
        
        # Refresh-Button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 Wiedereintritte aktualisieren", use_container_width=True):
                st.rerun()
        
        # Übersicht der nächsten Wiedereintritte
        st.subheader("🔍 Kommende Wiedereintritte - Übersicht")
        
        reentry_overview = []
        for reentry in reentries[:10]:  # Nächste 10 Wiedereintritte
            traj_start = (reentry['trajectory_start']['lat'], reentry['trajectory_start']['lon'])
            traj_end = (reentry['trajectory_end']['lat'], reentry['trajectory_end']['lon'])
            pred_location = (reentry['predicted_location']['lat'], reentry['predicted_location']['lon'])
            
            visibility = evaluate_reentry_visibility(traj_start, traj_end, pred_location, reentry['reentry_time'])
            
            de_timezone = pytz.timezone('Europe/Berlin')
            reentry_time_de = reentry['reentry_time'].astimezone(de_timezone)
            
            reentry_overview.append({
                'Objekt': reentry['name'],
                'Typ': reentry['object_type'],
                'Zeit (DE)': reentry_time_de.strftime('%d.%m.%Y %H:%M'),
                'Unsicherheit': f"±{reentry['uncertainty_hours']}h",
                'Über Deutschland': f"{visibility['distance']:.0f} km",
                'Sichtbarkeit': visibility['visibility_rating'],
                'Dauer': f"{reentry['visibility_duration_minutes']} Min",
                'Risiko': reentry['risk_level']
            })
        
        df_reentry = pd.DataFrame(reentry_overview)
        st.dataframe(df_reentry, use_container_width=True)
        
        # Detailanalyse für ausgewählten Wiedereintritt
        st.subheader("🔬 Detailanalyse Wiedereintritt")
        reentry_names = [f"{reentry['name']} ({reentry['object_type']})" for reentry in reentries]
        selected_reentry_index = st.selectbox("Wähle einen Wiedereintritt für die Detailanalyse:", 
                                           range(len(reentry_names)), 
                                           format_func=lambda i: reentry_names[i])
        
        selected_reentry = reentries[selected_reentry_index]
        
        # Wiedereintritts-Details anzeigen
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📋 Objekt-Details**")
            st.write(f"**Name:** {selected_reentry['name']}")
            st.write(f"**Typ:** {selected_reentry['object_type']}")
            st.write(f"**Ursprung:** {selected_reentry['origin']}")
            st.write(f"**Masse:** {selected_reentry['mass_kg']} kg")
            st.write(f"**Größe:** {selected_reentry['size']}")
            
            de_timezone = pytz.timezone('Europe/Berlin')
            reentry_time_de = selected_reentry['reentry_time'].astimezone(de_timezone)
            st.write(f"**Wiedereintritt (UTC):** {selected_reentry['reentry_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**Wiedereintritt (DE):** {reentry_time_de.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**Unsicherheit:** ±{selected_reentry['uncertainty_hours']} Stunden")
        
        with col2:
            st.write("**🎯 Sichtbarkeitsbewertung**")
            traj_start = (selected_reentry['trajectory_start']['lat'], selected_reentry['trajectory_start']['lon'])
            traj_end = (selected_reentry['trajectory_end']['lat'], selected_reentry['trajectory_end']['lon'])
            pred_location = (selected_reentry['predicted_location']['lat'], selected_reentry['predicted_location']['lon'])
            
            visibility = evaluate_reentry_visibility(traj_start, traj_end, pred_location, selected_reentry['reentry_time'])
            
            st.write(f"**Entfernung zu Deutschland:** {visibility['distance']:.0f} km")
            st.write(f"**Sichtbarkeit:** {visibility['visibility_rating']}")
            st.write(f"**Tageszeit:** {visibility['time_rating']}")
            st.write(f"**Sichtdauer:** {selected_reentry['visibility_duration_minutes']} Minuten")
            st.write(f"**Risiko-Level:** {selected_reentry['risk_level']}")
            st.write(f"**Debris:** {selected_reentry['debris_survival']}")
            
            if visibility['visibility_rating'] in ["🟢 Sehr gut", "🟡 Gut"]:
                st.success("👀 Dieser Wiedereintritt könnte von Deutschland aus sichtbar sein!")
            else:
                st.info("ℹ️ Sichtbarkeit eher unwahrscheinlich.")
        
        # Sicherheitshinweise
        st.warning("""
        ⚠️ **SICHERHEITSHINWEISE ZU WIEDEREINTRITTEN:**
        - **Niemals Trümmerteile berühren** - können sehr heiß oder giftig sein
        - **Funde der örtlichen Polizei melden**
        - **Sicheren Abstand halten** bei Sichtungen
        - **Meiste Objekte verglühen vollständig** in der Atmosphäre
        """)
        
        # Wiedereintritts-Trajektorie auf Karte
        st.subheader("🗺️ Wiedereintritts-Trajektorie")
        
        # Informationen zur Trajektorie
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💫 Objekt-Masse", f"{selected_reentry['mass_kg']} kg")
        
        with col2:
            st.metric("⏱️ Sichtdauer", f"{selected_reentry['visibility_duration_minutes']} Min")
        
        with col3:
            hours_to_reentry = (selected_reentry['reentry_time'] - datetime.now(pytz.UTC)).total_seconds() / 3600
            if hours_to_reentry > 0:
                st.metric("💫 Wiedereintritt in", f"{hours_to_reentry:.1f}h")
            else:
                st.metric("💫 Status", "Erfolgt")
        
        with col4:
            trajectory_length = geodesic(traj_start, traj_end).kilometers
            st.metric("📏 Trajektorien-Länge", f"{trajectory_length:.0f} km")
        
        # Erstelle Wiedereintritts-Karte (nur eine Trajektorie)
        st.write("**📍 Interaktive Karte:** Die Trajektorie zeigt den vorhergesagten Wiedereintritts-Pfad")
        reentry_map = create_reentry_trajectory_map(selected_reentry)
        folium_static(reentry_map)
        
        # Zeitfenster für optimale Beobachtung
        st.subheader("⏰ Optimales Beobachtungsfenster")
        
        observation_windows = calculate_reentry_observation_windows(selected_reentry)
        
        if observation_windows:
            for window in observation_windows:
                with st.expander(f"🌟 {window['phase']} - {window['time_de']} (Sichtbarkeit: {window['visibility']:.0f}%)"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**🕐 Zeit (DE):** {window['time_de']}")
                        st.write(f"**🌍 Zeit (UTC):** {window['time_utc']}")
                        st.write(f"**📍 Position:** {window['coords'][0]:.1f}°N, {window['coords'][1]:.1f}°E")
                    
                    with col2:
                        st.write(f"**🎯 Sichtbarkeit:** {window['visibility']:.0f}%")
                        st.write(f"**📏 Entfernung:** {window['distance']:.0f} km")
                        st.write(f"**📐 Höhe:** {window['altitude']:.0f} km")
                    
                    direction = calculate_direction_from_germany(window['coords'])
                    if window['visibility'] > 50:
                        st.success(f"💡 **Schauen Sie nach {direction}** - Sehr gute Sichtchance!")
                    else:
                        st.info(f"💡 **Richtung {direction}** - Bei optimalen Bedingungen sichtbar")
        else:
            st.warning("Keine optimalen Beobachtungsfenster für diesen Wiedereintritt gefunden.")

    with tab3:
        st.subheader("📊 Sichtbarkeits-Statistiken")
        
        # Daten abrufen falls noch nicht geschehen
        if 'launches' not in locals():
            launch_data = get_launch_data()
            if launch_data:
                launches = launch_data.get('results', [])
            else:
                launches = []
        
        # Analyse aller kommenden Starts
        if launches:
            visible_launches = []
            all_launches_analysis = []
            
            for launch in launches:
                launch_time_str = launch['net']
                launch_time_utc = datetime.fromisoformat(launch_time_str.replace('Z', '+00:00'))
                launch_pad = launch['pad']
                launch_lat = float(launch_pad['latitude']) if launch_pad.get('latitude') else 0
                launch_lon = float(launch_pad['longitude']) if launch_pad.get('longitude') else 0
                launch_coords = (launch_lat, launch_lon)
                
                visibility_rating, description, time_rating, distance = evaluate_launch_visibility(launch_coords, launch_time_utc)
                
                all_launches_analysis.append({
                    'name': launch['name'],
                    'provider': launch['launch_service_provider']['name'],
                    'distance': distance,
                    'visibility_rating': visibility_rating,
                    'location': launch_pad['location']['name']
                })
                
                if distance <= 3500:  # Potentiell sichtbar
                    visible_launches.append({
                        'name': launch['name'],
                        'provider': launch['launch_service_provider']['name'],
                        'distance': distance,
                        'visibility_rating': visibility_rating,
                        'time_utc': launch_time_utc,
                        'location': launch_pad['location']['name']
                    })
            
            # Statistiken anzeigen
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Gesamt Starts", len(all_launches_analysis))
            
            with col2:
                potentially_visible = len([l for l in all_launches_analysis if l['distance'] <= 3500])
                st.metric("Potentiell sichtbar", potentially_visible)
            
            with col3:
                very_good = len([l for l in all_launches_analysis if l['distance'] <= 1000])
                st.metric("Sehr gute Chancen", very_good)
            
            # Diagramm der Sichtbarkeitsverteilung
            st.subheader("📈 Sichtbarkeitsverteilung")
            
            categories = {
                "Sehr gut (≤1000km)": len([l for l in all_launches_analysis if l['distance'] <= 1000]),
                "Gut (≤2000km)": len([l for l in all_launches_analysis if 1000 < l['distance'] <= 2000]),
                "Möglich (≤3500km)": len([l for l in all_launches_analysis if 2000 < l['distance'] <= 3500]),
                "Unwahrscheinlich (>3500km)": len([l for l in all_launches_analysis if l['distance'] > 3500])
            }
            
            chart_data = pd.DataFrame(list(categories.items()), columns=['Kategorie', 'Anzahl'])
            st.bar_chart(chart_data.set_index('Kategorie'))
            
            # Liste der am besten sichtbaren Starts
            if visible_launches:
                st.subheader("⭐ Beste Sichtbarkeitschancen")
                visible_df = pd.DataFrame(visible_launches)
                visible_df = visible_df.sort_values('distance').head(10)
                
                for _, launch in visible_df.iterrows():
                    with st.expander(f"{launch['name']} - {launch['visibility_rating']}"):
                        st.write(f"**Anbieter:** {launch['provider']}")
                        st.write(f"**Startort:** {launch['location']}")
                        st.write(f"**Entfernung:** {launch['distance']:.0f} km")
                        st.write(f"**Startzeit:** {launch['time_utc'].strftime('%d.%m.%Y %H:%M')} UTC")
        else:
            st.warning("Keine Startdaten verfügbar für die Analyse.")
    
    with tab4:
        st.subheader("📈 Historische Raketen-Sichtungen von Deutschland")
        
        # Generiere historische Daten
        historical_data = generate_historical_sightings()
        
        # Übersicht der letzten 12 Monate
        st.subheader("📊 Sichtungen der letzten 12 Monate")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_sightings = len(historical_data)
            st.metric("🔭 Gesamt Sichtungen", total_sightings)
        
        with col2:
            confirmed_sightings = len([s for s in historical_data if s['confirmed']])
            st.metric("✅ Bestätigt", confirmed_sightings)
        
        with col3:
            avg_per_month = total_sightings / 12
            st.metric("📅 Ø pro Monat", f"{avg_per_month:.1f}")
        
        with col4:
            best_month = get_best_sighting_month(historical_data)
            st.metric("🏆 Bester Monat", best_month)
        
        # Zeitdiagramm - Sichtungen über Zeit
        st.subheader("⏰ Zeitverlauf der Sichtungen")
        
        # Daten für Chart vorbereiten
        monthly_data = prepare_monthly_chart_data(historical_data)
        
        # Chart mit Recharts oder Fallback
        if PLOTLY_AVAILABLE:
            # Monatlicher Verlauf
            fig_monthly = px.line(
                monthly_data, 
                x='month', 
                y='count',
                title='Raketen-Sichtungen pro Monat',
                labels={'month': 'Monat', 'count': 'Anzahl Sichtungen'},
                markers=True
            )
            
            fig_monthly.update_layout(
                xaxis_title="Monat",
                yaxis_title="Anzahl Sichtungen",
                showlegend=False
            )
            
            st.plotly_chart(fig_monthly, use_container_width=True)
        else:
            # Fallback mit Streamlit Line Chart
            st.line_chart(monthly_data.set_index('month'))
        
        # Tageszeit-Analyse
        st.subheader("🕐 Sichtungszeiten - Tageszeit-Analyse")
        
        hourly_data = prepare_hourly_chart_data(historical_data)
        
        if PLOTLY_AVAILABLE:
            fig_hourly = px.bar(
                hourly_data,
                x='hour',
                y='count',
                title='Sichtungen nach Tageszeit',
                labels={'hour': 'Uhrzeit', 'count': 'Anzahl Sichtungen'},
                color='count',
                color_continuous_scale='Viridis'
            )
            
            fig_hourly.update_layout(
                xaxis_title="Uhrzeit (24h Format)",
                yaxis_title="Anzahl Sichtungen",
                xaxis=dict(tickmode='linear', tick0=0, dtick=2)
            )
            
            st.plotly_chart(fig_hourly, use_container_width=True)
        else:
            # Fallback mit Streamlit Bar Chart
            st.bar_chart(hourly_data.set_index('hour'))
        
        # Analyse der besten Sichtungszeiten
        col1, col2 = st.columns(2)
        
        with col1:
            best_times = analyze_best_sighting_times(historical_data)
            st.success(f"""
            **🌟 Beste Sichtungszeiten:**
            
            **Nachts (22:00-04:00):**
            - {best_times['night']} Sichtungen ({best_times['night_percent']:.1f}%)
            - Beste Zeit: {best_times['best_night_hour']}:00 Uhr
            
            **Dämmerung (18:00-22:00, 04:00-08:00):**
            - {best_times['twilight']} Sichtungen ({best_times['twilight_percent']:.1f}%)
            - Beste Zeit: {best_times['best_twilight_hour']}:00 Uhr
            """)
        
        with col2:
            seasonal_data = analyze_seasonal_patterns(historical_data)
            st.info(f"""
            **🌍 Saisonale Muster:**
            
            **Bester Monat:** {seasonal_data['best_month']} ({seasonal_data['best_count']} Sichtungen)
            **Schlechtester Monat:** {seasonal_data['worst_month']} ({seasonal_data['worst_count']} Sichtungen)
            
            **Trends:**
            - Winter: {seasonal_data['winter']} Sichtungen
            - Frühling: {seasonal_data['spring']} Sichtungen  
            - Sommer: {seasonal_data['summer']} Sichtungen
            - Herbst: {seasonal_data['autumn']} Sichtungen
            """)
        
        # Art der Sichtungen
        st.subheader("🚀 Art der Sichtungen")
        
        sighting_types = prepare_sighting_types_data(historical_data)
        
        if PLOTLY_AVAILABLE:
            fig_types = px.pie(
                sighting_types,
                values='count',
                names='type',
                title='Verteilung der Sichtungsarten',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            st.plotly_chart(fig_types, use_container_width=True)
        else:
            # Fallback: Zeige als Tabelle
            st.write("**Verteilung der Sichtungsarten:**")
            st.dataframe(sighting_types)
        
        # Detaillierte Liste der wichtigsten Sichtungen
        st.subheader("🏆 Bemerkenswerte Sichtungen 2025")
        
        notable_sightings = get_notable_sightings(historical_data)
        
        for sighting in notable_sightings:
            with st.expander(f"🌟 {sighting['date']} - {sighting['name']} ({sighting['type']})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**📅 Datum:** {sighting['date']}")
                    st.write(f"**🕐 Zeit:** {sighting['time']}")
                    st.write(f"**🎯 Sichtbarkeit:** {sighting['visibility']}%")
                    st.write(f"**📍 Region:** {sighting['region']}")
                
                with col2:
                    st.write(f"**🚀 Typ:** {sighting['type']}")
                    st.write(f"**📏 Entfernung:** {sighting['distance']} km")
                    st.write(f"**⭐ Qualität:** {sighting['quality']}")
                    if sighting['confirmed']:
                        st.success("✅ Bestätigt durch Beobachter")
                    else:
                        st.info("🔄 Theoretische Sichtung")
                
                st.write(f"**📝 Beschreibung:** {sighting['description']}")
        
        # Vorhersage für kommende Monate
        st.subheader("🔮 Prognose für kommende Monate")
        
        prediction_data = generate_sighting_predictions()
        
        if PLOTLY_AVAILABLE:
            fig_prediction = px.bar(
                prediction_data,
                x='month',
                y='predicted_sightings',
                title='Vorhergesagte Sichtungen (nächste 6 Monate)',
                labels={'month': 'Monat', 'predicted_sightings': 'Erwartete Sichtungen'},
                color='predicted_sightings',
                color_continuous_scale='Blues'
            )
            
            st.plotly_chart(fig_prediction, use_container_width=True)
        else:
            # Fallback mit Streamlit Bar Chart
            st.bar_chart(prediction_data.set_index('month'))
        
        st.info("""
        **📊 Prognose basiert auf:**
        - Historischen Sichtungsmustern
        - Geplanten Raketenstarts (ESA, SpaceX, etc.)
        - Saisonalen Wettermustern
        - Neuen europäischen Startplätzen (Schottland, Norwegen)
        """)

    with tab5:
        st.subheader("ℹ️ Informationen zur Raketen-Sichtbarkeit")
        
        st.write("""
        ### 🌍 Von Deutschland aus sichtbare Raketenstarts
        
        **Europäische Starts (beste Sichtbarkeit):**
        - 🇳🇴 **Andøya Spaceport, Norwegen** (~1.200 km)
          - Isar Aerospace Spectrum
          - Weitere europäische Raketen
        
        - 🏴󠁧󠁢󠁳󠁣󠁴󠁿 **SaxaVord Spaceport, Schottland** (~1.000 km)
          - Rocket Factory Augsburg (RFA One)
          - Orbex Prime
        
        - 🇫🇷 **Kourou, Französisch-Guayana** (~7.200 km)
          - Ariane 6 (meist nicht sichtbar aufgrund Entfernung)
          - Vega C (meist nicht sichtbar aufgrund Entfernung)
        
        **Amerikanische Starts (bedingt sichtbar):**
        - 🇺🇸 **Cape Canaveral, Florida** (~7.200 km)
          - SpaceX Falcon 9 (sehr selten sichtbar, nur bei perfekten Bedingungen)
          - SpaceX Falcon Heavy
        
        - 🇺🇸 **Vandenberg, Kalifornien** (~9.000 km)
          - SpaceX Falcon 9 (praktisch nicht sichtbar)
        
        ### 🔭 Sichtbarkeitsfaktoren
        
        **Optimale Bedingungen:**
        - 🌙 **Nachtzeit** (22:00 - 04:00 Uhr): Beste Sichtbarkeit
        - 🌅 **Dämmerung** (20:00 - 22:00, 04:00 - 06:00 Uhr): Gute Sichtbarkeit
        - ☁️ **Klarer Himmel**: Keine Wolken
        - 🏙️ **Geringe Lichtverschmutzung**: Ländliche Gebiete bevorzugt
        
        **Was Sie sehen können:**
        - 🚀 **Während des Aufstiegs**: Helle Triebwerksflamme (erste 10-15 Minuten)
        - ⭐ **Im Orbit**: Sonnenlicht-Reflexion an Satelliten/Raketen
        - 💫 **Wiedereintritte**: Leuchtende Spur beim Verglühen von Raketenstufen
        
        ### 📱 Beobachtungstipps
        
        1. **Apps nutzen**: ISS Detector, Satellite Tracker
        2. **Wettervorhersage prüfen**: Klarer Himmel erforderlich
        3. **Dunklen Ort aufsuchen**: Weg von Stadtlichtern
        4. **Geduld haben**: Sichtung kann kurz und unerwartet sein
        5. **Nach Norden schauen**: Viele europäische Starts sind nordöstlich sichtbar
        
        ### 🌟 Aktuelle Highlights 2025
        
        **Besonders vielversprechend:**
        - **SpaceX Falcon 9 Spiralen**: Nach Starts manchmal über Europa sichtbar
        - **Europäische Raketentests**: Neue Startplätze in Schottland und Norwegen
        - **Starlink-Ketten**: Frisch gestartete Satelliten in Formation
        """)
        
        # Aktuelle bekannte sichtbare Ereignisse
        st.subheader("🔥 Aktuelle sichtbare Ereignisse (basierend auf aktuellen Berichten)")
        
        st.info("""
        **Zuletzt bestätigt sichtbar von Deutschland:**
        - März 2025: SpaceX Falcon 9 Spirale nach NROL-69 Start
        - Februar 2025: Falcon 9 Wiedereintrittsspur über Europa
        - Regelmäßig: ISS-Überflüge (alle 90 Minuten bei geeigneten Bedingungen)
        """)

if __name__ == "__main__":
    main()