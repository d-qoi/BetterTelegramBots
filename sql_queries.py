CREATE_TABLE_USER = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    firstname TEXT,
    lastname TEXT
);"""

CREATE_TABLE_MESSAGE = """
CREATE TABLE IF NOT EXISTS messages (
  user INTEGER,
  message_id INTEGER,
  from_user INTEGER,
  forwarded_from INTEGER,
  type TEXT,
  PRIMARY KEY (user, message_id),
  FOREIGN KEY (user, from_user, forwarded_from) REFERENCES users (user_id)
);"""

CREATE_TABLE_TEXT_MESSAGE = """
CREATE TABLE IF NOT EXISTS text_messages (
    user INTEGER,
    message INTEGER,
    received INTEGER,
    edited INTEGER,
    state TEXT CHECK (state IN ('new', 'edited', 'deleted')),
    content TEXT
    FOREIGN KEY (user) REFERENCES users (user_id),
    FOREIGN KEY (message) REFERENCES messages (message_id),
    PRIMARY KEY (message, edited)
);"""

CREATE_TABLE_FORWARDED_MESSAGE = """
CREATE TABLE IF NOT EXISTS fowarded_messages (
    user INTEGER,
    message INTEGER,
    from_user INTEGER,
    received INTEGER,
    edited INTEGER,
    state TEXT CHECK (state IN ('new', 'edited', 'deleted')),
    content TEXT
    FOREIGN KEY (user) REFERENCES users (user_id),
    FOREIGN KEY (from_user) REFERENCES users (user_id),
    FOREIGN KEY (message) REFERENCES messages (message_id),
    PRIMARY KEY (message, edited)
);"""
