CREATE TABLE train_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary key',
    departure_city VARCHAR(50) NOT NULL COMMENT 'Departure city, for example Sydney',
    arrival_city VARCHAR(50) NOT NULL COMMENT 'Arrival city, for example Melbourne',
    departure_time DATETIME NOT NULL COMMENT 'Departure time',
    arrival_time DATETIME NOT NULL COMMENT 'Arrival time',
    train_number VARCHAR(20) NOT NULL COMMENT 'Train number, for example ST21',
    seat_type VARCHAR(20) NOT NULL COMMENT 'Seat type, for example Economy',
    total_seats INT NOT NULL COMMENT 'Total seats',
    remaining_seats INT NOT NULL COMMENT 'Remaining seats',
    price DECIMAL(10, 2) NOT NULL COMMENT 'Price in AUD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Row creation time',
    UNIQUE KEY unique_train (departure_time, train_number)
) COMMENT='Train ticket table';

CREATE TABLE flight_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary key',
    departure_city VARCHAR(50) NOT NULL COMMENT 'Departure city, for example Sydney',
    arrival_city VARCHAR(50) NOT NULL COMMENT 'Arrival city, for example Melbourne',
    departure_time DATETIME NOT NULL COMMENT 'Departure time',
    arrival_time DATETIME NOT NULL COMMENT 'Arrival time',
    flight_number VARCHAR(20) NOT NULL COMMENT 'Flight number, for example QF401',
    cabin_type VARCHAR(20) NOT NULL COMMENT 'Cabin type, for example Economy',
    total_seats INT NOT NULL COMMENT 'Total seats',
    remaining_seats INT NOT NULL COMMENT 'Remaining seats',
    price DECIMAL(10, 2) NOT NULL COMMENT 'Price in AUD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Row creation time',
    UNIQUE KEY unique_flight (departure_time, flight_number)
) COMMENT='Flight ticket table';

CREATE TABLE concert_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Primary key',
    artist VARCHAR(100) NOT NULL COMMENT 'Artist name, for example Tame Impala',
    city VARCHAR(50) NOT NULL COMMENT 'City, for example Sydney',
    venue VARCHAR(100) NOT NULL COMMENT 'Venue, for example Qudos Bank Arena',
    start_time DATETIME NOT NULL COMMENT 'Start time',
    end_time DATETIME NOT NULL COMMENT 'End time',
    ticket_type VARCHAR(20) NOT NULL COMMENT 'Ticket type, for example VIP',
    total_seats INT NOT NULL COMMENT 'Total seats',
    remaining_seats INT NOT NULL COMMENT 'Remaining seats',
    price DECIMAL(10, 2) NOT NULL COMMENT 'Price in AUD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Row creation time',
    UNIQUE KEY unique_concert (start_time, artist, ticket_type)
) COMMENT='Concert ticket table';
