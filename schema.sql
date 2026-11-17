-- ORBIT MySQL schema (MySQL 8+). The app also creates these tables itself on first start,
-- so running this file is optional. Use it if you prefer to set the database up by hand.
--
--   mysql -u root -p < schema.sql
--   (then create an app user, see README.md)

CREATE DATABASE IF NOT EXISTS orbit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE orbit;

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(120) NOT NULL DEFAULT '', 
	password_hash VARCHAR(255) NOT NULL, 
	me_id VARCHAR(40), 
	is_sample BOOL NOT NULL DEFAULT '0', 
	created_at DATETIME DEFAULT (now()), 
	PRIMARY KEY (id), 
	UNIQUE (email)
)ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE constellations (
	user_id INTEGER NOT NULL, 
	id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	hue SMALLINT NOT NULL DEFAULT '260', 
	position INTEGER NOT NULL DEFAULT '0', 
	PRIMARY KEY (user_id, id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE memories (
	user_id INTEGER NOT NULL, 
	id VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	memory_date VARCHAR(10) NOT NULL DEFAULT '', 
	location VARCHAR(200) NOT NULL DEFAULT '', 
	body TEXT, 
	PRIMARY KEY (user_id, id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE people (
	user_id INTEGER NOT NULL, 
	id VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	relation VARCHAR(120) NOT NULL DEFAULT '', 
	birthday VARCHAR(5) NOT NULL DEFAULT '', 
	since_year SMALLINT NOT NULL DEFAULT '2026', 
	constellation_id VARCHAR(40), 
	hue SMALLINT NOT NULL DEFAULT '260', 
	orbit_ring SMALLINT NOT NULL DEFAULT '2', 
	note TEXT, 
	position INTEGER NOT NULL DEFAULT '0', 
	PRIMARY KEY (user_id, id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE timelines (
	user_id INTEGER NOT NULL, 
	id VARCHAR(40) NOT NULL, 
	year SMALLINT NOT NULL, 
	text VARCHAR(300) NOT NULL, 
	person_id VARCHAR(40), 
	PRIMARY KEY (user_id, id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE memory_participants (
	user_id INTEGER NOT NULL, 
	memory_id VARCHAR(40) NOT NULL, 
	person_id VARCHAR(40) NOT NULL, 
	PRIMARY KEY (user_id, memory_id, person_id), 
	FOREIGN KEY(user_id, memory_id) REFERENCES memories (user_id, id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id, person_id) REFERENCES people (user_id, id) ON DELETE CASCADE
)ENGINE=InnoDB CHARSET=utf8mb4;

CREATE TABLE relationships (
	user_id INTEGER NOT NULL, 
	person_a VARCHAR(40) NOT NULL, 
	person_b VARCHAR(40) NOT NULL, 
	label VARCHAR(120) NOT NULL DEFAULT 'Connected', 
	PRIMARY KEY (user_id, person_a, person_b), 
	FOREIGN KEY(user_id, person_a) REFERENCES people (user_id, id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id, person_b) REFERENCES people (user_id, id) ON DELETE CASCADE
)ENGINE=InnoDB CHARSET=utf8mb4;
