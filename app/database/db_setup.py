import sqlite3
from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution


class DatabaseManager:
    def __init__(self, db_path: str = "vidhan_sabha.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.setup_database()

    def setup_database(self):
        """Create database connection and initialize tables."""
        try:
            # Create database directory if it doesn't exist
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Connect to database
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Create tables
            self._create_tables()
            
            # Check and add lob column if needed
            self._ensure_lob_column_exists()
            
            print("Database setup completed successfully")
            
        except Exception as e:
            print(f"Error setting up database: {str(e)}")
            if self.conn:
                self.conn.close()
            raise

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        # Create sessions table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, 
            year TEXT NOT NULL,  
            type TEXT NOT NULL,  
            house TEXT NOT NULL, 
            status TEXT,
            user TEXT,
            last_update TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, type, house)
        )
        ''')

        # Create members table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL, 
            name TEXT NOT NULL,
            position TEXT,
            department TEXT,
            status TEXT,
            user TEXT,
            last_update TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            UNIQUE(session_id, name, position)
        )
        ''')

        # Create karyawali table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS karyawali (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,  
            number TEXT NOT NULL,  
            text TEXT NOT NULL, 
            status TEXT,
            user TEXT,
            last_update TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            UNIQUE(session_id, number)
        )
        ''')

        # Create kramank table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS kramank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,  
            number TEXT NOT NULL,  
            date TEXT NOT NULL,  
            chairman TEXT NOT NULL,
            path TEXT NOT NULL,
            full_ocr_text TEXT NOT NULL,
            status TEXT,
            user TEXT,
            last_update TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            UNIQUE(session_id, number)
        )
        ''')

        # Create debates table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS debates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kramank_id INTEGER NOT NULL,
            image_name TEXT NOT NULL,
            topic TEXT NOT NULL,
            text TEXT NOT NULL,
            date TEXT,
            question_number TEXT,  -- JSON array
            members TEXT,  -- JSON array
            topics TEXT,  -- JSON array
            answers_by TEXT,  -- JSON array
            lob TEXT,  -- JSON object for lob data
            status TEXT,
            user TEXT,
            last_update TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kramank_id) REFERENCES kramank (id)
        )
        ''')

        # Create debate_members junction table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS debate_members (
            debate_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            role TEXT NOT NULL,  -- e.g., 'speaker', 'responder'
            FOREIGN KEY (debate_id) REFERENCES debates (id),
            FOREIGN KEY (member_id) REFERENCES members (id),
            PRIMARY KEY (debate_id, member_id, role)
        )
        ''')

        self.conn.commit()

    def _ensure_lob_column_exists(self):
        """Ensure lob column exists in debates table (for existing databases)."""
        try:
            # Check if lob column exists
            self.cursor.execute("PRAGMA table_info(debates)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            if 'lob' not in columns:
                print("Adding lob column to existing debates table...")
                self.cursor.execute("ALTER TABLE debates ADD COLUMN lob TEXT")
                self.conn.commit()
                print("Successfully added lob column to debates table.")
        except Exception as e:
            print(f"Error ensuring lob column exists: {str(e)}")

    # INSERT_YOUR_CODE
    def insert_session(self, session):
        """
        Insert a new legislative session.
        Accepts a Session object (from session.py).
        """
        try:
            # Generate session ID from year, type and house
            session_id = f"{session.year}_{session.type}_{session.house}"

            # Set default values for status and user if not present
            status = getattr(session, 'status', None) or 'unauthorize'
            user = getattr(session, 'user', None) or 'admin'
            now = getattr(session, 'last_update', None) or datetime.now().isoformat()

            self.cursor.execute('''
            INSERT OR IGNORE INTO sessions (id, year, type, house, status, user, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                session.year,
                session.type,
                session.house,
                status,
                user,
                now
            ))
            self.conn.commit()
            return [session_id]
        except Exception as e:
            print(f"Error inserting session: {str(e)}")
            self.conn.rollback()
            return None

    # def insert_session(self, session: Dict):
    #     """Insert a new legislative session."""
    #     try:
    #         # Generate session ID from year, type and house
    #         session_id = f"{session['year']}_{session['type']}_{session['house']}"
            
    #         # Set default values for status and user if not present
    #         if 'status' not in session or session['status'] is None:
    #             session['status'] = 'unauthorize'
    #         if 'user' not in session or session['user'] is None:
    #             session['user'] = 'admin'
    #         now = session.get('last_update') or datetime.now().isoformat()
    #         self.cursor.execute('''
    #         INSERT OR IGNORE INTO sessions (id, year, type, house, status, user, last_update)
    #         VALUES (?, ?, ?, ?, ?, ?, ?)
    #         ''', (
    #             session_id,
    #             session['year'],
    #             session['type'],
    #             session['house'],
    #             session['status'],
    #             session['user'],
    #             now
    #         ))
    #         self.conn.commit()
    #         return session_id
    #     except Exception as e:
    #         print(f"Error inserting session: {str(e)}")
    #         self.conn.rollback()
    #         return None

    def insert_members(self, session_id: str, members: List['Member']):
        """Insert members for a specific session. Expects a list of Member data modal objects."""
        try:
            now = datetime.now().isoformat()
            for member in members:
                # If member is a Pydantic model, convert to dict
                if hasattr(member, "model_dump"):
                    member_dict = member.model_dump()
                else:
                    member_dict = dict(member)
                # Set default values for status and user if not present
                if member_dict.get('status') is None:
                    member_dict['status'] = 'unauthorize'
                if member_dict.get('user') is None:
                    member_dict['user'] = 'admin'
                # Insert into DB
                self.cursor.execute('''
                INSERT OR IGNORE INTO members (
                    session_id, name, position, department, status, user, last_update
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    member_dict.get('name'),
                    member_dict.get('position'),
                    member_dict.get('department'),
                    member_dict.get('status'),
                    member_dict.get('user'),
                    member_dict.get('last_update', now)
                ))
            self.conn.commit()
            print(f"Inserted {len(members)} members for session {session_id}")
        except Exception as e:
            print(f"Error inserting members: {str(e)}")
            self.conn.rollback()
    
    def insert_karyawali(self, session_id: str, karyawali: List['Resolution']):
        """Insert karyawali entries for a session using Resolution objects."""
        try:
            now = datetime.now().isoformat()
            for item in karyawali:
                # If item is a Pydantic model, convert to dict
                if hasattr(item, "model_dump"):
                    item_dict = item.model_dump()
                else:
                    item_dict = dict(item)
                # Set default values for status and user if not present
                if item_dict.get('status') is None:
                    item_dict['status'] = 'unauthorize'
                if item_dict.get('user') is None:
                    item_dict['user'] = 'admin'
                self.cursor.execute('''
                INSERT OR IGNORE INTO karyawali (
                    session_id, number, text, status, user, last_update
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    item_dict.get('number'),
                    item_dict.get('text'),
                    item_dict.get('status'),
                    item_dict.get('user'),
                    item_dict.get('last_update', now)
                ))
            self.conn.commit()
            print(f"Inserted {len(karyawali)} karyawali entries for session {session_id}")
        except Exception as e:
            print(f"Error inserting karyawali: {str(e)}")
            self.conn.rollback()
    
    def kramank_exists(self, session_id: str, name: str) -> bool:
        """
        Check if a kramank with the given session_id and name exists in the database.
        Returns True if exists, False otherwise.
        """

        try:
            self.cursor.execute(
                '''
                SELECT 1 FROM kramank
                WHERE session_id = ? AND number = ?
                LIMIT 1
                ''',
                (session_id, name)
            )
            result = self.cursor.fetchone()
            return result is not None
        except Exception as e:
            print(f"Error checking kramank existence: {str(e)}")
            return False


    def insert_kramank(self, session_id: str, kramank: Dict):
        """Insert a kramank entry."""
        try:
            
            if 'status' not in kramank or kramank['status'] is None:
                kramank['status'] = 'unauthorize'
            if 'user' not in kramank or kramank['user'] is None:
                kramank['user'] = 'admin'
            now = datetime.now().isoformat()
            self.cursor.execute('''
            INSERT OR IGNORE INTO kramank (
                session_id, number, date, chairman, path, full_ocr_text, status, user, last_update
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                kramank['number'],
                kramank['date'],
                kramank['chairman'],
                kramank['path'],
                kramank['full_ocr_text'],
                kramank.get('status'),
                kramank.get('user'),
                kramank.get('last_update', now)
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error inserting kramank: {str(e)}")
            self.conn.rollback()
            return None

    def insert_debate(self, kramank_id: int, debate: Dict):
        """Insert a debate and its related data."""
        try:
            # INSERT_YOUR_CODE
            if 'status' not in debate or debate['status'] is None:
                debate['status'] = 'unauthorize'
            if 'user' not in debate or debate['user'] is None:
                debate['user'] = 'admin'
            # Convert lists to JSON strings
            question_number_json = json.dumps(debate.get('question_number', []), ensure_ascii=False)
            members_json = json.dumps(debate.get('members', []), ensure_ascii=False)
            topics_json = json.dumps(debate.get('topics', []), ensure_ascii=False)
            answers_json = json.dumps(debate.get('answers_by', []), ensure_ascii=False)
            lob_json = json.dumps(debate.get('lob', {}), ensure_ascii=False)

            # Insert debate
            now = datetime.now().isoformat()
            self.cursor.execute('''
            INSERT INTO debates (
                kramank_id, image_name, topic, text, date,
                question_number, members, topics, answers_by, lob, status, user, last_update
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                kramank_id,
                debate['image_name'],
                debate['topic'],
                debate['text'],
                debate.get('date'),
                question_number_json,
                members_json,
                topics_json,
                answers_json,
                lob_json,
                debate.get('status'),
                debate.get('user'),
                debate.get('last_update', now)
            ))
            
            debate_id = self.cursor.lastrowid

            # Insert debate members relationships
            for member_name in debate.get('members', []):
                # Get member ID
                self.cursor.execute('''
                SELECT id FROM members 
                WHERE name = ? AND session_id = (
                    SELECT session_id FROM kramank WHERE id = ?
                )
                ''', (member_name, kramank_id))
                
                result = self.cursor.fetchone()
                if result:
                    member_id = result[0]
                    # Create debate-member relationship
                    self.cursor.execute('''
                    INSERT OR IGNORE INTO debate_members (debate_id, member_id, role)
                    VALUES (?, ?, ?)
                    ''', (debate_id, member_id, 'speaker'))

            self.conn.commit()
            print(f"Inserted debate: {debate['topic']}")
            return debate_id
            
        except Exception as e:
            print(f"Error inserting debate: {str(e)}")
            self.conn.rollback()
            return None

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def select_sessions(self):
        self.cursor.execute('SELECT * FROM sessions')
        return self.cursor.fetchall()

    def select_members(self):
        self.cursor.execute('SELECT * FROM members')
        return self.cursor.fetchall()

    def select_karyawali(self):
        self.cursor.execute('SELECT * FROM karyawali')
        return self.cursor.fetchall()

    def select_kramank(self):
        self.cursor.execute('SELECT * FROM kramank')
        return self.cursor.fetchall()

    def select_debates(self):
        self.cursor.execute('SELECT * FROM debates')
        return self.cursor.fetchall()

    def update_session(self, session_id, **kwargs):
        self._update_table('sessions', 'id', session_id, kwargs)

    def update_member(self, member_id, **kwargs):
        self._update_table('members', 'id', member_id, kwargs)

    def update_karyawali(self, karyawali_id, **kwargs):
        self._update_table('karyawali', 'id', karyawali_id, kwargs)

    def update_kramank(self, kramank_id, **kwargs):
        self._update_table('kramank', 'id', kramank_id, kwargs)

    def update_debate(self, debate_id, **kwargs):
        self._update_table('debates', 'id', debate_id, kwargs)

    def _update_table(self, table, pk_col, pk_val, updates):
        if not updates:
            return
        set_clause = ', '.join([f"{col} = ?" for col in updates.keys()])
        values = list(updates.values())
        values.append(pk_val)
        sql = f"UPDATE {table} SET {set_clause}, last_update = ? WHERE {pk_col} = ?"
        values.insert(-1, datetime.now().isoformat())
        self.cursor.execute(sql, values)
        self.conn.commit()

def setup_database():
    """Create a new database instance and set up tables."""
    db_manager = DatabaseManager()
    return db_manager 