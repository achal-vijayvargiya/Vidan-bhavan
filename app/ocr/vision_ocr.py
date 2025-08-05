# ocr/vision_ocr.py

from google.cloud import vision
import os
import io
from google.cloud.vision_v1 import types
from typing import List, Tuple
from app.logging.logger import Logger


logger = Logger()

def setup_vision_client():
    # Get the absolute path to the credentials file
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    credentials_path = os.path.join(base_dir, "app", "config", "gcp_config.json")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    return vision.ImageAnnotatorClient()

def extract_text_from_image(image_path):
    client = setup_vision_client()

    with open(image_path, "rb") as img_file:
        content = img_file.read()

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)

    return response.full_text_annotation.text
