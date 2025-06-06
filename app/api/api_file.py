from app.ocr.vision_ocr import extract_text_from_image
from app.extractor.field_extractor_marathi import  extract_fields_from_marathi_text
def getData(image_path):
    text = extract_text_from_image(image_path)
    json=extract_fields_from_marathi_text(text)
    return json;