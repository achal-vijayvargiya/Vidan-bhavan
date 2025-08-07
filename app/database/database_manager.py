from typing import List, Dict, Optional
from .db_setup import DatabaseManager
import json
from datetime import datetime
from app.logging.logger import Logger
from app.data_modals.session import Session
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution
from app.data_modals.debate import Debate
logger = Logger()


class DataManager:
    def __init__(self, db_path: str = "vidhan_sabha.db"):
        """Initialize the data manager with database connection."""
        self.db = DatabaseManager(db_path)

    def insert_session(self, sessions: List[Session]) -> List[Optional[str]]:
        """Insert multiple sessions. Accepts a list of session objects."""
        try:
            session_ids = []
            for session_obj in sessions:
                session_id = self.db.insert_session(session_obj)
                session_ids.append(session_id)
            return session_ids
        except Exception as e:
            print(f"Error inserting sessions: {str(e)}")
            return []

    def insert_members(self, session_id: str, members: List[Member]) -> List[Optional[int]]:
        """Insert multiple members for a session. Expects a list of Member data modal objects."""
        try:
            self.db.insert_members(session_id, members)
            member_ids = []
            self.db.cursor.execute('SELECT last_insert_rowid()')
            member_ids.append(self.db.cursor.fetchone()[0])
            # for member_obj in members:
            #     # Pass the Member object directly to insert_members
            #     self.db.insert_members(session_id, [member_obj])
            #     self.db.cursor.execute('SELECT last_insert_rowid()')
            #     member_ids.append(self.db.cursor.fetchone()[0])
            # self.db.conn.commit()
            return member_ids
        except Exception as e:
            print(f"Error inserting members: {str(e)}")
            return []

    def insert_karyawali(self, session_id: str, karyawali_list: List[Resolution]) -> List[Optional[int]]:
        """Insert multiple karyawali entries for a session."""
        try:
            karyawali_ids = []
            for karyawali in karyawali_list:
                self.db.insert_karyawali(session_id, [karyawali])
                self.db.cursor.execute('SELECT last_insert_rowid()')
                karyawali_ids.append(self.db.cursor.fetchone()[0])
            self.db.conn.commit()
            return karyawali_ids
        except Exception as e:
            print(f"Error inserting karyawali: {str(e)}")
            return []
   
    def check_kramank_exists(self, session_id: str, name: str) -> bool:
        """
        Calls kramank_exists from the database manager and returns the result.
        """
        return self.db.kramank_exists(session_id, name)


    def insert_kramank(self, session_id: str, kramank_list: List[Dict]) -> List[Optional[int]]:
        """Insert multiple kramank entries."""
        try:
            kramank_ids = []
            for kramank in kramank_list:
                kramank_id = self.db.insert_kramank(session_id, kramank)
                kramank_ids.append(kramank_id)
            self.db.conn.commit()
            return kramank_ids
        except Exception as e:
            print(f"Error inserting kramank: {str(e)}")
            return []

    def insert_debate(self, kramank_id: int, debates: List[Debate]) -> List[Optional[int]]:
        """Insert multiple debate entries."""
        try:
            debate_ids = []
            for debate in debates:
                # Convert lists to JSON strings
                logger.info(f"debate: {debate}")
                question_number_json = json.dumps(debate.get('question_number', []), ensure_ascii=False)
                members_json = json.dumps(debate.get('members', []), ensure_ascii=False)
                topics_json = json.dumps(debate.get('topics', []), ensure_ascii=False)
                answers_json = json.dumps(debate.get('answers_by', []), ensure_ascii=False)
                lob_json = json.dumps(debate.get('debate_type', {}), ensure_ascii=False)
                image_name_json = json.dumps(debate.get('image_name', {}), ensure_ascii=False)
                topic_json = json.dumps(debate.get('topic', {}), ensure_ascii=False)
                text_json = json.dumps(debate.get('text', {}), ensure_ascii=False)
                date_json = json.dumps(debate.get('date', {}), ensure_ascii=False)
                # Insert debate
                self.db.cursor.execute('''
                INSERT INTO debates (
                    kramank_id, image_name, topic, text, date,
                    question_number, members, topics, answers_by, lob
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    kramank_id,
                    json.dumps(image_name_json, ensure_ascii=False),
                    json.dumps(topic_json, ensure_ascii=False),
                    json.dumps(text_json, ensure_ascii=False),
                    json.dumps(date_json, ensure_ascii=False),
                    json.dumps(question_number_json, ensure_ascii=False),
                    json.dumps(members_json, ensure_ascii=False),
                    json.dumps(topics_json, ensure_ascii=False),
                    json.dumps(answers_json, ensure_ascii=False),
                    json.dumps(lob_json, ensure_ascii=False)
                ))
                debate_id = self.db.cursor.lastrowid
                debate_ids.append(debate_id)

                # Insert debate members relationships
                

            self.db.conn.commit()
            return debate_ids
        except Exception as e:
            print(f"Error inserting debates: {str(e)}")
            return []

    def insert_debate_member(self, debate_members: List[Dict]) -> List[bool]:
        """Insert multiple debate-member relationships."""
        try:
            results = []
            for relation in debate_members:
                self.db.cursor.execute('''
                INSERT OR IGNORE INTO debate_members (debate_id, member_id, role)
                VALUES (?, ?, ?)
                ''', (
                    relation['debate_id'],
                    relation['member_id'],
                    relation['role']
                ))
                results.append(True)
            self.db.conn.commit()
            return results
        except Exception as e:
            print(f"Error inserting debate members: {str(e)}")
            return []

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get complete session data including all related information."""
        try:
            # Get session details
            self.db.cursor.execute('''
            SELECT year, type, house FROM sessions WHERE id = ?
            ''', (session_id,))
            session = self.db.cursor.fetchone()
            if not session:
                return None

            result = {
                'session': {
                    'id': session_id,
                    'year': session[0],
                    'type': session[1],
                    'house': session[2]
                }
            }

            # Get members
            self.db.cursor.execute('''
            SELECT name, position, department FROM members WHERE session_id = ?
            ''', (session_id,))
            members = [{'name': row[0], 'position': row[1], 'department': row[2]} 
                      for row in self.db.cursor.fetchall()]
            result['members'] = members

            # Get karyawali
            self.db.cursor.execute('''
            SELECT number, text FROM karyawali WHERE session_id = ?
            ''', (session_id,))
            karyawali = [{'number': row[0], 'text': row[1]} 
                        for row in self.db.cursor.fetchall()]
            result['karyawali'] = karyawali

            # Get kramank and debates
            self.db.cursor.execute('''
            SELECT id, number, date, chairman, path, full_ocr_text 
            FROM kramank WHERE session_id = ?
            ''', (session_id,))
            kramank_list = []
            for kramank_row in self.db.cursor.fetchall():
                kramank_id = kramank_row[0]
                kramank = {
                    'number': kramank_row[1],
                    'date': kramank_row[2],
                    'chairman': kramank_row[3],
                    'path': kramank_row[4],
                    'full_ocr_text': kramank_row[5]
                }

                # Get debates for this kramank
                self.db.cursor.execute('''
                SELECT image_name, topic, text, date, question_number, 
                       members, topics, answers_by, lob
                FROM debates WHERE kramank_id = ?
                ''', (kramank_id,))
                debates = []
                for debate_row in self.db.cursor.fetchall():
                    debate = {
                        'image_name': debate_row[0],
                        'topic': debate_row[1],
                        'text': debate_row[2],
                        'date': debate_row[3],
                        'question_number': json.loads(debate_row[4]),
                        'members': json.loads(debate_row[5]),
                        'topics': json.loads(debate_row[6]),
                        'answers_by': json.loads(debate_row[7]),
                        'lob': json.loads(debate_row[8]) if debate_row[8] else {}
                    }
                    debates.append(debate)
                kramank['debates'] = debates
                kramank_list.append(kramank)

            result['kramank'] = kramank_list
            return result

        except Exception as e:
            print(f"Error retrieving session data: {str(e)}")
            return None

    
    def get_all_sessions(self):
        self.db.cursor.execute('SELECT * FROM sessions')
        columns = [desc[0] for desc in self.db.cursor.description]
        return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]

    def get_all_members(self):
        self.db.cursor.execute('SELECT * FROM members')
        columns = [desc[0] for desc in self.db.cursor.description]
        return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]

    def get_members_by_session_id(self, session_id: str):
        """
        Retrieve all members records for a given session_id.
        """
        self.db.cursor.execute('SELECT * FROM members WHERE session_id = ?', (session_id,))
        columns = [desc[0] for desc in self.db.cursor.description]
        return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]
    
    def get_karyawali_by_session_id(self, session_id: str):
        """
        Retrieve all karyawali records for a given session_id.
        """
        cur = self.db.conn.cursor()
        cur.execute('SELECT * FROM karyawali WHERE session_id = ?', (session_id,))
        columns = [desc[0] for desc in cur.description]
        result = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return result

    def get_all_karyawali(self):
        self.db.cursor.execute('SELECT * FROM karyawali')
        columns = [desc[0] for desc in self.db.cursor.description]
        return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]

    def get_all_kramank(self):
        self.db.cursor.execute('SELECT * FROM kramank')
        columns = [desc[0] for desc in self.db.cursor.description]
        return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]

    def get_debates_count(self):
        """
        Returns the total count of debates in the database.
        """
        self.db.cursor.execute('SELECT COUNT(*) FROM debates')
        result = self.db.cursor.fetchone()
        return result[0] if result else 0
    
    def get_all_debates(self):
        self.db.cursor.execute('SELECT * FROM debates')
        columns = [desc[0] for desc in self.db.cursor.description]
        return [dict(zip(columns, row)) for row in self.db.cursor.fetchall()]

    def get_debates_by_session_id(self, session_id: str) -> list:
        """
        Retrieve all debates for a given session_id.
        """
        try:
            # Use a new cursor for the outer query
            cur_outer = self.db.conn.cursor()
            cur_outer.execute('SELECT id FROM kramank WHERE session_id = ?', (session_id,))
            kramank_ids = [row[0] for row in cur_outer.fetchall()]
            cur_outer.close()
            if not kramank_ids:
                return []

            debates = []
            for kramank_id in kramank_ids:
                cur_inner = self.db.conn.cursor()
                cur_inner.execute('SELECT * FROM debates WHERE kramank_id = ?', (kramank_id,))
                columns = [desc[0] for desc in cur_inner.description]
                for row in cur_inner.fetchall():
                    debate = dict(zip(columns, row))
                    # Attempt to decode JSON fields if present
                    for field in ['question_number', 'members', 'topics', 'answers_by', 'lob']:
                        if field in debate and debate[field] is not None:
                            try:
                                debate[field] = json.loads(debate[field])
                            except Exception:
                                pass
                    debates.append(debate)
                cur_inner.close()
            return debates
        except Exception as e:
            print(f"Error retrieving debates for session {session_id}: {str(e)}")
            return []

    def get_kramank_by_number(self, session_id: str, number: str) -> Optional[Dict]:
        """Get specific kramank with its debates."""
        try:
            self.db.cursor.execute('''
            SELECT id, date, chairman, path, full_ocr_text 
            FROM kramank 
            WHERE session_id = ? AND number = ?
            ''', (session_id, number))
            kramank_row = self.db.cursor.fetchone()
            if not kramank_row:
                return None

            kramank = {
                'number': number,
                'date': kramank_row[1],
                'chairman': kramank_row[2],
                'path': kramank_row[3],
                'full_ocr_text': kramank_row[4]
            }

            # Get debates
            self.db.cursor.execute('''
            SELECT image_name, topic, text, date, question_number, 
                   members, topics, answers_by, lob
            FROM debates 
            WHERE kramank_id = ?
            ''', (kramank_row[0],))
            debates = []
            for debate_row in self.db.cursor.fetchall():
                debate = {
                    'image_name': debate_row[0],
                    'topic': debate_row[1],
                    'text': debate_row[2],
                    'date': debate_row[3],
                    'question_number': json.loads(debate_row[4]),
                    'members': json.loads(debate_row[5]),
                    'topics': json.loads(debate_row[6]),
                    'answers_by': json.loads(debate_row[7]),
                    'lob': json.loads(debate_row[8]) if debate_row[8] else {}
                }
                debates.append(debate)
            kramank['debates'] = debates
            return kramank

        except Exception as e:
            print(f"Error retrieving kramank: {str(e)}")
            return None

    def search_debates(self, session_id: str, search_term: str) -> List[Dict]:
        """Search debates by topic or text content."""
        try:
            self.db.cursor.execute('''
            SELECT d.image_name, d.topic, d.text, d.date, d.question_number, 
                   d.members, d.topics, d.answers_by, d.lob, k.number as kramank_number
            FROM debates d
            JOIN kramank k ON d.kramank_id = k.id
            WHERE k.session_id = ? 
            AND (d.topic LIKE ? OR d.text LIKE ?)
            ''', (session_id, f'%{search_term}%', f'%{search_term}%'))
            
            debates = []
            for row in self.db.cursor.fetchall():
                debate = {
                    'kramank_number': row[9],
                    'image_name': row[0],
                    'topic': row[1],
                    'text': row[2],
                    'date': row[3],
                    'question_number': json.loads(row[4]),
                    'members': json.loads(row[5]),
                    'topics': json.loads(row[6]),
                    'answers_by': json.loads(row[7]),
                    'lob': json.loads(row[8]) if row[8] else {}
                }
                debates.append(debate)
            return debates

        except Exception as e:
            print(f"Error searching debates: {str(e)}")
            return []

    def close(self):
        """Close the database connection."""
        self.db.close() 