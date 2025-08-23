import os
from typing import List
from datetime import datetime
from PIL import Image
from PyPDF2 import PdfWriter, PdfReader
from sqlalchemy import text
from sqlalchemy.orm import Session

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
    
    def _convert_images_to_pdf(self, image_paths: List[str], output_path: str) -> bool:
        """
        Convert a list of images to a single PDF file
        
        Args:
            image_paths (List[str]): List of image file paths
            output_path (str): Path where the PDF should be saved
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            pdf_writer = PdfWriter()
            
            for img_path in image_paths:
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
                    
                # Save image as temporary PDF
                temp_pdf = "temp.pdf"
                image.save(temp_pdf, "PDF", resolution=100.0)
                
                # Add page to final PDF
                pdf_reader = PdfReader(temp_pdf)
                pdf_writer.add_page(pdf_reader.pages[0])
                
                # Clean up temp file
                os.remove(temp_pdf)
            
            # Save the final PDF
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
                
            return True
        except Exception as e:
            self.logger.error(f"Error converting images to PDF: {str(e)}")
            return False
            
    def process_debate_images(self, debate_id: int) -> str:
        """
        Process images for a specific debate and generate PDF
        
        Args:
            debate_id (int): ID of the debate to process
            
        Returns:
            str: Generated PDF filename or empty string if failed
        """
        db = next(get_db())
        try:
            # Fetch debate record with topic and image_name
            query = text("""
                SELECT image_name, topic 
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
            
            # Convert images to PDF
            if self._convert_images_to_pdf(image_paths, pdf_path):
                # Update database with the new document name
                update_query = text("""
                    UPDATE debates 
                    SET document_name = :doc_name 
                    WHERE debate_id = :debate_id
                """)
                db.execute(update_query, {
                    "doc_name": pdf_filename,
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
            
    def process_all_pending_debates(self) -> List[str]:
        """
        Process all debates that don't have a document_name yet
        
        Returns:
            List[str]: List of generated PDF filenames
        """
        db = next(get_db())
        try:
            # Fetch all debates 
            query = text("""
                SELECT debate_id 
                FROM debates 
                WHERE image_name IS NOT NULL
            """)
            results = db.execute(query).fetchall()
            
            generated_pdfs = []
            for row in results:
                pdf_filename = self.process_debate_images(row[0])
                if pdf_filename:
                    generated_pdfs.append(pdf_filename)
                    
            return generated_pdfs
            
        except Exception as e:
            self.logger.error(f"Error processing pending debates: {str(e)}")
            return []
        finally:
            db.close()
