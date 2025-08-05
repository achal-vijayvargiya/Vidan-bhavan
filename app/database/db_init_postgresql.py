from app.data_modals.session import Session
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution
from app.data_modals.kramank import Kramank
from app.data_modals.debate import Debate
from app.data_modals.Base import Base
from app.database.db_conn_postgresql import engine


# Create all tables in the database
def createtables():
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    print("All tables created.") 