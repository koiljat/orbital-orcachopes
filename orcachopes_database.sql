CREATE DATABASE ORCAChopes;

USE ORCAChopes;

CREATE TABLE Facility (
  id INT NOT NULL,
  facility_name VARCHAR(32) NOT NULL,
  PRIMARY KEY (facility_name)
);

INSERT INTO Facility (id, facility_name) VALUES
  (1, 'Pool Table'),
  (2, 'Mahjong Table'),
  (3, 'Foosball'),
  (4, 'Darts');

CREATE TABLE Users (
  username VARCHAR(32) NOT NULL,
  first_name VARCHAR(32),
  last_name VARCHAR(32),
  PRIMARY KEY (username)
);

CREATE TABLE Bookings (
  booking_id INT AUTO_INCREMENT NOT NULL,
  facility_name VARCHAR(32) NOT NULL,
  username VARCHAR(32) NOT NULL,
  `datetime` DATETIME NOT NULL,
  `date` DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  cancelled BOOLEAN NOT NULL,
  reminder BOOLEAN NOT NULL,
  PRIMARY KEY (booking_id),
  FOREIGN KEY (facility_name) REFERENCES Facility(facility_name),
  FOREIGN KEY (username) REFERENCES Users(username)
);

CREATE TABLE Reports (
	report_id INT AUTO_INCREMENT NOT NULL,
    username VARCHAR(32) NOT NULL,
    `datetime` DATETIME NOT NULL,
    remarks VARCHAR(150) NOT NULL,
    PRIMARY KEY(report_id),
	FOREIGN KEY (username) REFERENCES Users(username)
    );