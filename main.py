import subprocess
import sys
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

def run_streamlit_app():
    # Get the absolute path to app.py
    app_path = os.path.join(BASE_DIR, "ui", "streamlit_app.py")
    # Run streamlit app
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])

if __name__ == "__main__":
    run_streamlit_app()
