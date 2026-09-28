DROP DATABASE IF EXISTS travel_rag;
CREATE DATABASE travel_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE travel_rag;

CREATE TABLE train_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY, -- Primary key, auto-increment, uniquely identifies each record
    departure_city VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Departure city (for example, "Beijing")
    arrival_city VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Arrival city (for example, "Shanghai")
    departure_time DATETIME NOT NULL, -- Departure time (for example, "2025-08-12 07:00:00")
    arrival_time DATETIME NOT NULL, -- Arrival time (for example, "2025-08-12 11:30:00")
    train_number VARCHAR(20) NOT NULL, -- Train number (for example, "G1001")
    seat_type VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Seat type (for example, "Second class")
    total_seats INT NOT NULL, -- Total number of seats (for example, 1000)
    remaining_seats INT NOT NULL, -- Remaining seats (for example, 50)
    price DECIMAL(10, 2) NOT NULL, -- Ticket price (for example, 553.50)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Creation time, automatically records the insert time
    UNIQUE KEY unique_train (departure_time, train_number) -- Unique constraint so the same departure time and train number are not duplicated
);

CREATE TABLE flight_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY, -- Primary key, auto-increment, uniquely identifies each record
    departure_city VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Departure city (for example, "Beijing")
    arrival_city VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Arrival city (for example, "Shanghai")
    departure_time DATETIME NOT NULL, -- Departure time (for example, "2025-08-12 08:00:00")
    arrival_time DATETIME NOT NULL, -- Arrival time (for example, "2025-08-12 10:30:00")
    flight_number VARCHAR(20) NOT NULL, -- Flight number (for example, "CA1234")
    cabin_type VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Cabin type (for example, "Economy")
    total_seats INT NOT NULL, -- Total number of seats (for example, 200)
    remaining_seats INT NOT NULL, -- Remaining seats (for example, 10)
    price DECIMAL(10, 2) NOT NULL, -- Ticket price (for example, 1200.00)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Creation time, automatically records the insert time
    UNIQUE KEY unique_flight (departure_time, flight_number) -- Unique constraint so the same departure time and flight number are not duplicated
);

CREATE TABLE concert_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY, -- Primary key, auto-increment, uniquely identifies each record
    artist VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Artist name (for example, "Jay Chou")
    city VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Host city (for example, "Shanghai")
    venue VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Venue (for example, "Shanghai Stadium")
    start_time DATETIME NOT NULL, -- Start time (for example, "2025-08-12 19:00:00")
    end_time DATETIME NOT NULL, -- End time (for example, "2025-08-12 22:00:00")
    ticket_type VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, -- Ticket type (for example, "VIP")
    total_seats INT NOT NULL, -- Total number of seats (for example, 5000)
    remaining_seats INT NOT NULL, -- Remaining seats (for example, 100)
    price DECIMAL(10, 2) NOT NULL, -- Ticket price (for example, 880.00)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Creation time, automatically records the insert time
    UNIQUE KEY unique_concert (start_time, artist, ticket_type) -- Unique constraint so the same start time, artist, and ticket type are not duplicated
);

DROP TABLE IF EXISTS weather_data;
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
) ENGINE=INNODB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Weather data table';
