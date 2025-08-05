from app.database.database_manager import DataManager

def store_debate_data(debates_data, kramank_id):
    """
    Store the extracted debate data in the database.
    Returns the DB insert result.
    """
    data_manager = DataManager()

    data_manager.insert_debate(kramank_id, debates_data)
    
    print("debate data stored !!")
    
    return True 