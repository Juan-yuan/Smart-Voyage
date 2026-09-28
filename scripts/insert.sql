USE travel_rag;

-- 30 test rows for a traveler based in Sydney.
-- 10 trains, 8 flights, 6 concerts, 6 weather forecasts.
-- Prices are AUD. Dates are local time in October 2026.

INSERT INTO train_tickets (
    departure_city, arrival_city, departure_time, arrival_time,
    train_number, seat_type, total_seats, remaining_seats, price
) VALUES
    ('Sydney', 'Melbourne', '2026-10-03 07:40:00', '2026-10-03 18:30:00', 'ST21', 'Economy', 258, 46, 141.00),
    ('Sydney', 'Melbourne', '2026-10-03 20:42:00', '2026-10-04 07:30:00', 'ST23', 'First class', 52, 8, 268.00),
    ('Melbourne', 'Sydney', '2026-10-05 08:20:00', '2026-10-05 19:05:00', 'ST22', 'Economy', 258, 71, 139.50),
    ('Sydney', 'Brisbane', '2026-10-04 14:35:00', '2026-10-05 04:50:00', 'ST1', 'Economy', 228, 33, 176.00),
    ('Brisbane', 'Sydney', '2026-10-06 15:10:00', '2026-10-07 05:25:00', 'ST2', 'Economy', 228, 54, 169.00),
    ('Sydney', 'Canberra', '2026-10-02 06:55:00', '2026-10-02 11:05:00', 'NT31', 'Economy', 180, 62, 48.00),
    ('Sydney', 'Newcastle', '2026-10-02 07:15:00', '2026-10-02 09:42:00', 'H210', 'Economy', 640, 210, 18.50),
    ('Sydney', 'Wollongong', '2026-10-02 08:05:00', '2026-10-02 09:32:00', 'SC112', 'Economy', 720, 305, 12.80),
    ('Sydney', 'Katoomba', '2026-10-03 08:48:00', '2026-10-03 10:46:00', 'BMT45', 'Economy', 560, 188, 10.50),
    ('Sydney', 'Bathurst', '2026-10-04 09:20:00', '2026-10-04 12:55:00', 'WT17', 'Economy', 160, 27, 35.00);

INSERT INTO flight_tickets (
    departure_city, arrival_city, departure_time, arrival_time,
    flight_number, cabin_type, total_seats, remaining_seats, price
) VALUES
    ('Sydney', 'Melbourne', '2026-10-02 06:30:00', '2026-10-02 08:05:00', 'QF401', 'Economy', 180, 24, 179.00),
    ('Sydney', 'Melbourne', '2026-10-02 18:15:00', '2026-10-02 19:50:00', 'VA807', 'Business', 12, 3, 642.00),
    ('Melbourne', 'Sydney', '2026-10-05 16:40:00', '2026-10-05 18:10:00', 'QF418', 'Economy', 180, 41, 165.00),
    ('Sydney', 'Brisbane', '2026-10-03 09:10:00', '2026-10-03 10:40:00', 'QF501', 'Economy', 174, 19, 158.00),
    ('Brisbane', 'Sydney', '2026-10-06 19:05:00', '2026-10-06 20:35:00', 'QF508', 'Economy', 174, 36, 149.00),
    ('Sydney', 'Gold Coast', '2026-10-04 11:25:00', '2026-10-04 12:45:00', 'JQ401', 'Economy', 186, 52, 119.00),
    ('Sydney', 'Canberra', '2026-10-02 07:50:00', '2026-10-02 08:50:00', 'VA260', 'Economy', 76, 11, 142.00),
    ('Sydney', 'Auckland', '2026-10-07 09:45:00', '2026-10-07 14:55:00', 'NZ101', 'Economy', 270, 64, 448.00);

INSERT INTO concert_tickets (
    artist, city, venue, start_time, end_time,
    ticket_type, total_seats, remaining_seats, price
) VALUES
    ('Tame Impala', 'Sydney', 'Qudos Bank Arena', '2026-10-16 19:30:00', '2026-10-16 22:15:00', 'General', 14000, 860, 169.00),
    ('Tame Impala', 'Sydney', 'Qudos Bank Arena', '2026-10-16 19:30:00', '2026-10-16 22:15:00', 'VIP', 400, 22, 429.00),
    ('Missy Higgins', 'Sydney', 'Sydney Opera House', '2026-10-18 20:00:00', '2026-10-18 22:00:00', 'Reserved', 1500, 95, 128.00),
    ('Paul Kelly', 'Sydney', 'Enmore Theatre', '2026-10-23 19:30:00', '2026-10-23 22:00:00', 'General', 1600, 140, 99.00),
    ('Hilltop Hoods', 'Sydney', 'Accor Stadium', '2026-10-30 18:30:00', '2026-10-30 22:00:00', 'General', 20000, 2400, 155.00),
    ('Angie McMahon', 'Sydney', 'Hordern Pavilion', '2026-11-06 19:00:00', '2026-11-06 21:30:00', 'General', 5500, 410, 89.00);

INSERT INTO weather_data (
    city, fx_date, sunrise, sunset, moonrise, moonset,
    moon_phase, moon_phase_icon, temp_max, temp_min,
    icon_day, text_day, icon_night, text_night,
    wind360_day, wind_dir_day, wind_scale_day, wind_speed_day,
    wind360_night, wind_dir_night, wind_scale_night, wind_speed_night,
    precip, uv_index, humidity, pressure, vis, cloud, update_time
) VALUES
    ('Sydney', '2026-10-02', '05:42:00', '18:02:00', '14:10:00', '02:35:00', 'Waning gibbous', '805', 23, 15, '101', 'Partly cloudy', '151', 'Cloudy', 45, 'NE', '3', 18, 270, 'W', '2', 10, 0.4, 6, 68, 1016, 20, 45, '2026-10-01 18:00:00'),
    ('Melbourne', '2026-10-02', '06:12:00', '18:38:00', '14:28:00', '03:05:00', 'Waning gibbous', '805', 18, 10, '305', 'Light rain', '307', 'Showers', 225, 'SW', '4', 28, 200, 'SSW', '3', 16, 4.2, 3, 78, 1011, 12, 80, '2026-10-01 18:00:00'),
    ('Brisbane', '2026-10-02', '05:18:00', '17:46:00', '13:55:00', '02:10:00', 'Waning gibbous', '805', 27, 18, '100', 'Sunny', '150', 'Clear', 90, 'E', '3', 16, 110, 'ESE', '2', 9, 0.0, 8, 62, 1014, 24, 15, '2026-10-01 18:00:00'),
    ('Canberra', '2026-10-02', '05:58:00', '18:12:00', '14:18:00', '02:48:00', 'Waning gibbous', '805', 20, 6, '100', 'Sunny', '104', 'Overcast', 315, 'NW', '3', 20, 290, 'WNW', '2', 12, 0.0, 7, 48, 1018, 30, 10, '2026-10-01 18:00:00'),
    ('Newcastle', '2026-10-02', '05:38:00', '17:58:00', '14:06:00', '02:28:00', 'Waning gibbous', '805', 24, 16, '101', 'Partly cloudy', '151', 'Cloudy', 45, 'NE', '3', 19, 20, 'NNE', '2', 11, 0.2, 6, 70, 1015, 18, 40, '2026-10-01 18:00:00'),
    ('Gold Coast', '2026-10-02', '05:16:00', '17:44:00', '13:52:00', '02:06:00', 'Waning gibbous', '805', 26, 18, '100', 'Sunny', '150', 'Clear', 90, 'E', '3', 17, 80, 'E', '2', 8, 0.0, 9, 66, 1013, 22, 20, '2026-10-01 18:00:00');
