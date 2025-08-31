import os
import tempfile
from typing import List, Dict
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy import text
from sqlalchemy.orm import Session
import io

from app.database.db_conn_postgresql import get_db
from app.logging.logger import Logger

class PdfGenerater:
    def __init__(self, output_dir: str = "generated_pdfs", image_base_path: str = None):
        """
        Initialize PdfGenerater with output directory for PDFs and base path for images
        
        Args:
            output_dir (str): Directory where generated PDFs will be stored
            image_base_path (str): Base directory path where debate images are stored
        """
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Set and validate image base path
        self.image_base_path = image_base_path
        if self.image_base_path and not os.path.exists(self.image_base_path):
            raise ValueError(f"Image base path does not exist: {self.image_base_path}")
        
        # Initialize logger
        self.logger = Logger()
            
    def _generate_unique_filename(self, topic: str) -> str:
        """
        Generate a unique filename for the PDF based on debate topic and timestamp
        
        Args:
            topic (str): The debate topic to include in filename
            
        Returns:
            str: A unique filename containing the topic and timestamp
        """
        # Clean the topic string to make it filesystem-friendly
        clean_topic = "".join(c if c.isalnum() or c in ['-', '_', ' '] else '_' for c in topic)
        clean_topic = clean_topic.strip().replace(' ', '_')[:100]  # Limit length and replace spaces
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{clean_topic}_{timestamp}.pdf"
    
    def _convert_images_to_pdf(self, image_paths: List[str], output_path: str, ocr_results: Dict = None) -> bool:
        """
        Convert a list of images to a single PDF file with searchable text layers
        
        Args:
            image_paths (List[str]): List of image file paths
            output_path (str): Path where the PDF should be saved
            ocr_results (Dict): OCR results containing bounding box information
            
        Returns:
            bool: True if successful, False otherwise
        """
        temp_files = []  # Track all temporary files for cleanup
        
        try:
            pdf_writer = PdfWriter()
            
            for i, img_path in enumerate(image_paths):
                if not os.path.exists(img_path):
                    self.logger.warning(f"Image not found at path: {img_path}")
                    self.logger.warning(f"Base path being used: {self.image_base_path}")
                    continue
                self.logger.info(f"Processing image: {img_path}")
                    
                # Open image and convert to PDF
                image = Image.open(img_path)
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                # Create temporary PDF file with proper temp directory
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf_file:
                    temp_pdf_path = temp_pdf_file.name
                    temp_files.append(temp_pdf_path)
                
                # Save image as temporary PDF
                image.save(temp_pdf_path, "PDF", resolution=100.0)
                
                # Add page to final PDF
                pdf_reader = PdfReader(temp_pdf_path)
                page = pdf_reader.pages[0]
                
                # Add searchable text layer if OCR results are available
                if ocr_results and 'debates' in ocr_results:
                    # Find matching OCR data for this image
                    image_name = os.path.basename(img_path)
                    matching_ocr = None
                    for debate_page in ocr_results['debates']:
                        if debate_page.get('image_name') == image_name:
                            matching_ocr = debate_page
                            break
                    
                    if matching_ocr and 'bounding_boxes' in matching_ocr:
                        # Create text layer PDF
                        text_layer_pdf = self._create_text_layer_pdf(
                            matching_ocr['bounding_boxes'], 
                            image.size[0], 
                            image.size[1]
                        )
                        
                        if text_layer_pdf:
                            temp_files.append(text_layer_pdf)
                            
                            # Merge text layer with image PDF
                            text_reader = PdfReader(text_layer_pdf)
                            text_page = text_reader.pages[0]
                            
                            # Overlay text layer on image page
                            page.merge_page(text_page)
                        else:
                            self.logger.warning(f"Failed to create text layer for image: {image_name}")
                
                pdf_writer.add_page(page)
            
            # Save the final PDF
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error converting images to PDF: {str(e)}")
            return False
            
        finally:
            # Clean up all temporary files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        self.logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as cleanup_error:
                    self.logger.warning(f"Failed to clean up temporary file {temp_file}: {str(cleanup_error)}")
            
    def _create_text_layer_pdf(self, bounding_boxes: Dict, image_width: int, image_height: int) -> str:
        """
        Create a PDF with invisible text positioned according to bounding boxes
        
        Args:
            bounding_boxes (Dict): Bounding box information from OCR
            image_width (int): Width of the original image
            image_height (int): Height of the original image
            
        Returns:
            str: Path to the temporary text layer PDF
        """
        try:
            # Create a temporary PDF file for the text layer using proper temp directory
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_text_pdf = temp_file.name
            
            # Create PDF with same dimensions as image
            c = canvas.Canvas(temp_text_pdf, pagesize=(image_width, image_height))
            
            # Set font (using a standard font that supports Devanagari)
            c.setFont("Helvetica", 8)  # Small font size for precise positioning
            
            # Process words from bounding boxes
            if 'words' in bounding_boxes:
                for word_data in bounding_boxes['words']:
                    if 'text' in word_data and 'bounding_box' in word_data:
                        word_text = word_data['text']
                        bbox = word_data['bounding_box']
                        
                        if 'vertices' in bbox and len(bbox['vertices']) >= 4:
                            # Get bounding box coordinates
                            vertices = bbox['vertices']
                            x_coords = [v[0] for v in vertices]
                            y_coords = [v[1] for v in vertices]
                            
                            # Calculate position (use bottom-left corner)
                            x = min(x_coords)
                            y = image_height - max(y_coords)  # Flip Y coordinate for PDF
                            
                            # Add invisible text
                            c.setFillAlpha(0.0)  # Make text invisible
                            c.drawString(x, y, word_text)
            
            # Process paragraphs for better text flow
            if 'paragraphs' in bounding_boxes:
                for para_data in bounding_boxes['paragraphs']:
                    if 'words' in para_data:
                        para_text = ""
                        for word_data in para_data['words']:
                            if 'text' in word_data:
                                para_text += word_data['text'] + " "
                        
                        if para_text.strip():
                            # Use paragraph bounding box for positioning
                            if 'bounding_box' in para_data and 'vertices' in para_data['bounding_box']:
                                bbox = para_data['bounding_box']
                                vertices = bbox['vertices']
                                x_coords = [v[0] for v in vertices]
                                y_coords = [v[1] for v in vertices]
                                
                                x = min(x_coords)
                                y = image_height - max(y_coords)
                                
                                # Add invisible paragraph text
                                c.setFillAlpha(0.0)
                                c.drawString(x, y, para_text.strip())
            
            c.save()
            return temp_text_pdf
            
        except Exception as e:
            self.logger.error(f"Error creating text layer PDF: {str(e)}")
            # Create empty PDF in temp directory if there's an error
            try:
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    temp_text_pdf = temp_file.name
                c = canvas.Canvas(temp_text_pdf, pagesize=(image_width, image_height))
                c.save()
                return temp_text_pdf
            except Exception as fallback_error:
                self.logger.error(f"Failed to create fallback text layer PDF: {str(fallback_error)}")
                return None
            
    def process_debate_images(self, debate_id: int, ocr_results: Dict = None) -> str:
        """
        Process images for a specific debate and generate PDF with searchable text
        
        Args:
            debate_id (int): ID of the debate to process
            ocr_results (Dict): OCR results containing bounding box information
            
        Returns:
            str: Generated PDF filename or empty string if failed
        """
        db = next(get_db())
        try:
            # Fetch debate record with topic and image_name
            query = text("""
                SELECT image_name, title as topic 
                FROM debates 
                WHERE debate_id = :debate_id
            """)
            result = db.execute(query, {"debate_id": debate_id}).first()
            
            if not result or not result[0]:
                self.logger.warning(f"No images found for debate ID: {debate_id}")
                return ""
            
            image_name, topic = result[0], result[1]
            if not topic:
                topic = "untitled_debate"  # Default topic if none exists
                
            # Parse image paths and add base path if provided
            image_paths = []
            for path in image_name.strip('{}').split(','):
                if self.image_base_path:
                    full_path = os.path.join(self.image_base_path, path.strip())
                else:
                    full_path = path.strip()  # Use path as is if no base path provided
                image_paths.append(full_path)
            
            # Generate unique filename for the PDF using topic
            pdf_filename = self._generate_unique_filename(topic)
            pdf_path = os.path.join(self.output_dir, pdf_filename)
            
            # Convert images to PDF with searchable text layer
            if self._convert_images_to_pdf(image_paths, pdf_path, ocr_results):
                # Update database with the new document name
                update_query = text("""
                    UPDATE debates 
                    SET document_name = :doc_name 
                    WHERE debate_id = :debate_id
                """)
                db.execute(update_query, {
                    "doc_name": pdf_path,
                    "debate_id": debate_id
                })
                db.commit()
                return pdf_filename
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error processing debate images: {str(e)}")
            db.rollback()
            return ""
        finally:
            db.close()
            
    def process_all_pending_debates(self, ocr_results) -> List[str]:
        """
        Process all debates that don't have a document_name yet
        
        Args:
            ocr_results (Dict): OCR results containing bounding box information
            
        Returns:
            List[str]: List of generated PDF filenames
        """
        db = next(get_db())
        try:
            # Extract kramank_id from ocr_results.debate_ids structure
            debate_ids_data = ocr_results.get('debate_ids', {})
            kramank_id = list(debate_ids_data.keys())[0] if debate_ids_data else None
            
            if not kramank_id:
                self.logger.warning("No kramank_id found in ocr_results")
                return []
            
            # Fetch all debates for this kramank
            query = text("""
                SELECT debate_id 
                FROM debates 
                WHERE image_name IS NOT NULL 
                AND kramank_id = :kramank_id
            """)
            results = db.execute(query, {"kramank_id": kramank_id}).fetchall()
            
            generated_pdfs = []
            for row in results:
                pdf_filename = self.process_debate_images(row[0], ocr_results)
                if pdf_filename:
                    generated_pdfs.append(pdf_filename)
                    
            return generated_pdfs
            
        except Exception as e:
            self.logger.error(f"Error processing pending debates: {str(e)}")
            return []
        finally:
            db.close()
