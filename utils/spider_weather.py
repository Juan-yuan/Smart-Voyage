import importlib.util
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pymysql
import requests

project_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)


def _load_project_module(module_name):
    """Load a module from the Smart-Voyage project directory."""
    module_path = os.path.join(project_directory, f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


Config = _load_project_module("config").Config
logger = _load_project_module("create_logger").logger

SYDNEY_TIMEZONE = timezone(timedelta(hours=10))
try:
    from zoneinfo import ZoneInfo

    SYDNEY_TIMEZONE = ZoneInfo("Australia/Sydney")
except Exception:
    logger.warning("Australia/Sydney timezone data is unavailable; using UTC+10.")

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 16

# Australian cities used by the Smart-Voyage ticket data, with Sydney first.
AUSTRALIAN_CITIES = {
    "Sydney": (-33.8688, 151.2093),
    "Melbourne": (-37.8136, 144.9631),
    "Brisbane": (-27.4698, 153.0251),
    "Canberra": (-35.2809, 149.1300),
    "Newcastle": (-32.9283, 151.7817),
    "Wollongong": (-34.4278, 150.8931),
    "Katoomba": (-33.7139, 150.3114),
    "Bathurst": (-33.4193, 149.5775),
    "Gold Coast": (-28.0167, 153.4000),
}

WEATHER_TEXT = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm hail",
    99: "Thunderstorm hail",
}

CREATE_WEATHER_TABLE = """
CREATE TABLE IF NOT EXISTS weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    city VARCHAR(50) NOT NULL COMMENT 'City name',
    fx_date DATE NOT NULL COMMENT 'Forecast date',
    sunrise TIME COMMENT 'Sunrise time',
    sunset TIME COMMENT 'Sunset time',
    moonrise TIME COMMENT 'Moonrise time',
    moonset TIME COMMENT 'Moonset time',
    moon_phase VARCHAR(20) COMMENT 'Moon phase name',
    moon_phase_icon VARCHAR(10) COMMENT 'Moon phase icon code',
    temp_max INT COMMENT 'Maximum temperature',
    temp_min INT COMMENT 'Minimum temperature',
    icon_day VARCHAR(10) COMMENT 'Daytime weather icon code',
    text_day VARCHAR(20) COMMENT 'Daytime weather description',
    icon_night VARCHAR(10) COMMENT 'Nighttime weather icon code',
    text_night VARCHAR(20) COMMENT 'Nighttime weather description',
    wind360_day INT COMMENT 'Daytime wind direction in degrees',
    wind_dir_day VARCHAR(20) COMMENT 'Daytime wind direction',
    wind_scale_day VARCHAR(10) COMMENT 'Daytime wind scale',
    wind_speed_day INT COMMENT 'Daytime wind speed (km/h)',
    wind360_night INT COMMENT 'Nighttime wind direction in degrees',
    wind_dir_night VARCHAR(20) COMMENT 'Nighttime wind direction',
    wind_scale_night VARCHAR(10) COMMENT 'Nighttime wind scale',
    wind_speed_night INT COMMENT 'Nighttime wind speed (km/h)',
    precip DECIMAL(5,1) COMMENT 'Precipitation (mm)',
    uv_index INT COMMENT 'UV index',
    humidity INT COMMENT 'Relative humidity (%)',
    pressure INT COMMENT 'Atmospheric pressure (hPa)',
    vis INT COMMENT 'Visibility (km)',
    cloud INT COMMENT 'Cloud cover (%)',
    update_time DATETIME COMMENT 'Data update time',
    UNIQUE KEY unique_city_date (city, fx_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Weather data table'
"""


def _db_config():
    config = Config()
    return {
        "host": config.host,
        "user": config.user,
        "password": config.password,
        "database": config.database,
        "charset": "utf8mb4",
    }


def connect_db():
    return pymysql.connect(**_db_config())


def _clip(value, limit):
    if value is None:
        return None
    return str(value)[:limit]


def _as_int(value):
    if value is None:
        return None
    return int(round(float(value)))


def _clock_time(value):
    if not value or "T" not in value:
        return None
    return value.split("T", 1)[1][:5] + ":00"


def _weather_text(code):
    if code is None:
        return None
    return WEATHER_TEXT.get(int(code), "Unknown")


def _wind_direction_name(degrees):
    if degrees is None:
        return None
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((float(degrees) + 22.5) // 45) % 8
    return names[index]


def _beaufort_scale(speed_kmh):
    if speed_kmh is None:
        return None
    limits = [1, 5, 11, 19, 28, 38, 49, 61, 74, 88, 102, 117]
    speed = float(speed_kmh)
    for scale, limit in enumerate(limits):
        if speed <= limit:
            return str(scale)
    return "12"


def _circular_mean(degrees):
    values = [float(item) for item in degrees if item is not None]
    if not values:
        return None
    east = sum(math.sin(math.radians(item)) for item in values)
    north = sum(math.cos(math.radians(item)) for item in values)
    if east == 0 and north == 0:
        return None
    return (math.degrees(math.atan2(east, north)) + 360) % 360


def _mean(values):
    numbers = [float(item) for item in values if item is not None]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def _most_common(values):
    counts = {}
    for item in values:
        if item is None:
            continue
        counts[item] = counts.get(item, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _moon_phase(day):
    known_new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)
    age = ((noon - known_new_moon).total_seconds() / 86400) % 29.53058867
    phases = [
        (1.84566, "New moon", "800"),
        (5.53699, "Waxing crescent", "801"),
        (9.22831, "First quarter", "802"),
        (12.91963, "Waxing gibbous", "803"),
        (16.61096, "Full moon", "804"),
        (20.30228, "Waning gibbous", "805"),
        (23.99361, "Last quarter", "806"),
        (27.68493, "Waning crescent", "807"),
    ]
    for limit, name, icon in phases:
        if age < limit:
            return name, icon
    return "New moon", "800"


def _hourly_indexes(hourly_times, start, end):
    indexes = []
    for index, stamp in enumerate(hourly_times):
        moment = datetime.fromisoformat(stamp)
        if start <= moment < end:
            indexes.append(index)
    return indexes


def _pick(series, indexes):
    if not series:
        return []
    return [series[index] for index in indexes if index < len(series)]


def fetch_weather_data(city, latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Australia/Sydney",
        "forecast_days": FORECAST_DAYS,
        "wind_speed_unit": "kmh",
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "sunrise",
            "sunset",
            "precipitation_sum",
            "uv_index_max",
            "wind_speed_10m_max",
            "wind_direction_10m_dominant",
        ]),
        "hourly": ",".join([
            "relative_humidity_2m",
            "surface_pressure",
            "cloud_cover",
            "visibility",
            "wind_speed_10m",
            "wind_direction_10m",
            "weather_code",
        ]),
    }
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        logger.error(f"Failed to request weather data for {city}: {error}")
        return None
    except ValueError as error:
        logger.error(f"Failed to parse weather JSON for {city}: {error}")
        return None
    if "daily" not in data:
        logger.error(f"Weather response for {city} did not include a daily forecast.")
        return None
    return data


def _forecast_rows(city, data):
    daily = data["daily"]
    hourly = data.get("hourly", {})
    hourly_times = hourly.get("time", [])
    updated_at = datetime.now(SYDNEY_TIMEZONE).replace(tzinfo=None)
    rows = []
    for index, date_text in enumerate(daily["time"]):
        forecast_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        day_start = datetime.combine(forecast_date, datetime.min.time()).replace(hour=6)
        day_end = day_start.replace(hour=18)
        night_start = day_end
        night_end = day_start + timedelta(days=1)
        day_indexes = _hourly_indexes(hourly_times, day_start, day_end)
        night_indexes = _hourly_indexes(hourly_times, night_start, night_end)

        day_code = _most_common(_pick(hourly.get("weather_code"), day_indexes))
        night_code = _most_common(_pick(hourly.get("weather_code"), night_indexes))
        if day_code is None:
            day_code = daily["weather_code"][index]
        if night_code is None:
            night_code = day_code

        day_direction = _circular_mean(_pick(hourly.get("wind_direction_10m"), day_indexes))
        night_direction = _circular_mean(_pick(hourly.get("wind_direction_10m"), night_indexes))
        if day_direction is None:
            day_direction = daily["wind_direction_10m_dominant"][index]
        if night_direction is None:
            night_direction = day_direction

        day_speed = _mean(_pick(hourly.get("wind_speed_10m"), day_indexes))
        night_speed = _mean(_pick(hourly.get("wind_speed_10m"), night_indexes))
        if day_speed is None:
            day_speed = daily["wind_speed_10m_max"][index]
        if night_speed is None:
            night_speed = day_speed

        humidity = _mean(_pick(hourly.get("relative_humidity_2m"), day_indexes + night_indexes))
        pressure = _mean(_pick(hourly.get("surface_pressure"), day_indexes + night_indexes))
        cloud = _mean(_pick(hourly.get("cloud_cover"), day_indexes + night_indexes))
        visibility_m = _mean(_pick(hourly.get("visibility"), day_indexes + night_indexes))
        visibility_km = None if visibility_m is None else visibility_m / 1000
        phase_name, phase_icon = _moon_phase(forecast_date)
        precip = daily["precipitation_sum"][index]

        rows.append((
            city,
            forecast_date,
            _clock_time(daily["sunrise"][index]),
            _clock_time(daily["sunset"][index]),
            None,
            None,
            _clip(phase_name, 20),
            _clip(phase_icon, 10),
            _as_int(daily["temperature_2m_max"][index]),
            _as_int(daily["temperature_2m_min"][index]),
            _clip(day_code, 10),
            _clip(_weather_text(day_code), 20),
            _clip(night_code, 10),
            _clip(_weather_text(night_code), 20),
            _as_int(day_direction),
            _clip(_wind_direction_name(day_direction), 20),
            _clip(_beaufort_scale(day_speed), 10),
            _as_int(day_speed),
            _as_int(night_direction),
            _clip(_wind_direction_name(night_direction), 20),
            _clip(_beaufort_scale(night_speed), 10),
            _as_int(night_speed),
            None if precip is None else round(float(precip), 1),
            _as_int(daily["uv_index_max"][index]),
            _as_int(humidity),
            _as_int(pressure),
            _as_int(visibility_km),
            _as_int(cloud),
            updated_at,
        ))
    return rows


def get_latest_update_time(cursor, city):
    cursor.execute("SELECT MAX(update_time) FROM weather_data WHERE city = %s", (city,))
    result = cursor.fetchone()
    return result[0] if result and result[0] else None


def should_update_data(latest_time, force_update=False):
    if force_update or not latest_time:
        return True
    if getattr(latest_time, "tzinfo", None) is not None:
        latest_time = latest_time.astimezone(SYDNEY_TIMEZONE).replace(tzinfo=None)
    current_time = datetime.now(SYDNEY_TIMEZONE).replace(tzinfo=None)
    elapsed_seconds = (current_time - latest_time).total_seconds()
    return elapsed_seconds >= 24 * 3600 or elapsed_seconds < 0


def store_weather_data(conn, cursor, city, data):
    rows = _forecast_rows(city, data)
    if not rows:
        logger.error(f"No forecast rows to store for {city}.")
        return

    insert_query = """
        INSERT INTO weather_data (
            city, fx_date, sunrise, sunset, moonrise, moonset, moon_phase, moon_phase_icon,
            temp_max, temp_min, icon_day, text_day, icon_night, text_night,
            wind360_day, wind_dir_day, wind_scale_day, wind_speed_day,
            wind360_night, wind_dir_night, wind_scale_night, wind_speed_night,
            precip, uv_index, humidity, pressure, vis, cloud, update_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            sunrise = VALUES(sunrise), sunset = VALUES(sunset), moonrise = VALUES(moonrise),
            moonset = VALUES(moonset), moon_phase = VALUES(moon_phase), moon_phase_icon = VALUES(moon_phase_icon),
            temp_max = VALUES(temp_max), temp_min = VALUES(temp_min), icon_day = VALUES(icon_day),
            text_day = VALUES(text_day), icon_night = VALUES(icon_night), text_night = VALUES(text_night),
            wind360_day = VALUES(wind360_day), wind_dir_day = VALUES(wind_dir_day),
            wind_scale_day = VALUES(wind_scale_day), wind_speed_day = VALUES(wind_speed_day),
            wind360_night = VALUES(wind360_night), wind_dir_night = VALUES(wind_dir_night),
            wind_scale_night = VALUES(wind_scale_night), wind_speed_night = VALUES(wind_speed_night),
            precip = VALUES(precip), uv_index = VALUES(uv_index), humidity = VALUES(humidity),
            pressure = VALUES(pressure), vis = VALUES(vis), cloud = VALUES(cloud),
            update_time = VALUES(update_time)
    """
    try:
        cursor.executemany(insert_query, rows)
        conn.commit()
        logger.info(f"Stored {len(rows)} forecast days for {city}. Latest daytime weather: {rows[0][11]}.")
    except pymysql.Error as error:
        conn.rollback()
        logger.error(f"Database error while storing weather for {city}: {error}")


def ensure_weather_table(conn, cursor):
    cursor.execute(CREATE_WEATHER_TABLE)
    conn.commit()


def update_weather(force_update=False):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        ensure_weather_table(conn, cursor)
        for city, (latitude, longitude) in AUSTRALIAN_CITIES.items():
            latest_time = get_latest_update_time(cursor, city)
            if not should_update_data(latest_time, force_update):
                logger.info(f"{city} weather is already up to date. Latest update: {latest_time}.")
                continue
            logger.info(f"Updating weather for {city}...")
            data = fetch_weather_data(city, latitude, longitude)
            if data:
                store_weather_data(conn, cursor, city, data)
    finally:
        cursor.close()
        conn.close()


def setup_scheduler():
    logger.info("Scheduling a daily weather update at 01:00 Australia/Sydney.")
    last_run_date = None
    while True:
        now = datetime.now(SYDNEY_TIMEZONE)
        if now.hour == 1 and last_run_date != now.date():
            update_weather()
            last_run_date = now.date()
        time.sleep(30)


if __name__ == "__main__":
    if "--schedule" in sys.argv:
        update_weather()
        setup_scheduler()
    else:
        update_weather(force_update=True)
        logger.info("Weather update finished.")
