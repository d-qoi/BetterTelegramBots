CREATE_TABLE_USER = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    firstname TEXT,
    lastname TEXT
);"""

INSERT_USER = """
INSERT OR IGNORE INTO users values(?, ?, ?, ?);
"""

CREATE_TABLE_MESSAGE = """
CREATE TABLE IF NOT EXISTS messages (
  chat_id INTEGER,
  message_id INTEGER,
  from_user INTEGER,
  forwarded_from INTEGER,
  reply_to INTEGER,
  received INTEGER,
  state TEXT CHECK (state IN ('new', 'edited', 'deleted')),
  type TEXT CHECK (type IN ('text', 'audio', 'document', 'photo', 'sticker', 'video', 'animation', 'voice', 'video_note', 'contact', 'location', 'venue')),
  PRIMARY KEY (message_id, received),
  FOREIGN KEY (from_user) REFERENCES users (user_id),
  FOREIGN KEY (forwarded_from) REFERENCES users (user_id)
);"""

INSERT_MESSAGE = """
INSERT INTO messages values(?, ?, ?, ?, ?, ?, ?, ?);
"""

SELECT_MESSAGE_BY_ID = """
SELECT message_id FROM messages WHERE message_id=?;
"""

CREATE_TABLE_TEXT_MESSAGE = """
CREATE TABLE IF NOT EXISTS text_messages (
    message INTEGER,
    content TEXT,
    FOREIGN KEY (message) REFERENCES messages (message_id)
);"""

INSERT_TEXT_MESSAGE = """
INSERT INTO text_messages values(?, ?);
"""

CREATE_TABLE_FILE_MESSAGE = """
CREATE TABLE IF NOT EXISTS file_messages (
    message INTEGER,
    file_id TEXT,
    file_name TEXT,
    mime_type TEXT,
    date INTEGER,
    caption TEXT,
    FOREIGN KEY (message) REFERENCES messages (message_id)
);"""

INSERT_FILE = """
INSERT INTO file_messages values(?,?,?,?,?,?);
"""

CREATE_TABLE_CONTACT_MESSAGE = """
CREATE TABLE IF NOT EXISTS contacts (
    message INTEGER,
    phone_number TEXT,
    first_name TEXT,
    last_name TEXT,
    user_id INTEGER,
    vcard TEXT,
    FOREIGN KEY (message) REFERENCES messages (message_id),
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);"""

INSERT_CONTACT = """
INSERT INTO contacts values(?,?,?,?,?,?);
"""

CREATE_TABLE_LOCATION = """
CREATE TABLE IF NOT EXISTS locations (
    message INTEGER,
    loc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL,
    lon REAL,
    FOREIGN KEY (message) REFERENCES messages (message_id)
);"""

INSERT_LOCATION = """
INSERT INTO location (message, lat, long) values (?,?,?);
"""

CREATE_TABLE_VENUE = """
CREATE TABLE IF NOT EXISTS venues (
    message INTEGER,
    location INTEGER,
    title TEXT,
    address TEXT,
    foursquare_id TEXT,
    foursquare_type TEXT,
    FOREIGN KEY (message) REFERENCES messages (message_id),
    FOREIGN KEY (location) REFERENCES locations (loc_id)
);"""

INSERT_VENUE = """
INSERT INTO venues values(?,?,?,?,?,?);
"""

CREATE_TABLE_OTHER_MESSAGE = """
CREATE TABLE IF NOT EXISTS other_messages (
    message INTEGER,
    json TEXT,
    FOREIGN KEY (message) REFERENCES messages (message_id)
);"""

INSERT_OTHER_MESSAGE = """
INSERT INTO other_messages values(?,?);
"""
