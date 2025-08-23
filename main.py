import subprocess
import sys
import os
from dotenv import load_dotenv
from pathlib import Path
from app.kramak_reader.agent import agent_run
from app.database.db_init_postgresql import createtables
from app.logging.logger import Logger
from app.debate_agent.pdf_generater import PdfGenerater

# Initialize logger
logger = Logger()

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

# BALANCED PRODUCTION: Configuration constants
MAX_FOLDERS_TO_PROCESS = 100  # BALANCED: Increased from 3 for better productivity
ENABLE_BATCH_PROCESSING = True  # Set to True only when needed

def run_streamlit_app():
    # Get the absolute path to app.py
    app_path = os.path.join(BASE_DIR, "ui", "streamlit_app.py")
    # Run streamlit app
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def run_agent_on_all_kramank_folders(base_path):
    """
    Recursively find all folders named 'Kramank_*' under base_path and run agent_run on each.
    COST OPTIMIZED: Includes batch limits and safety checks.
    """
    logger.info("run_agent_on_all_kramank_folders called with COST PROTECTION")
    
    # COST OPTIMIZATION: Safety check
    if not ENABLE_BATCH_PROCESSING:
        logger.warning("🚨 COST PROTECTION: Batch processing is DISABLED to prevent high API costs.")
        logger.warning("🚨 To enable batch processing, set ENABLE_BATCH_PROCESSING = True in main.py")
        logger.warning("🚨 This will process multiple folders and may incur significant LLM costs.")
        return
    
    base_path = Path(base_path)
    kramank_folders = []
    
    try:
        for root, dirs, files in os.walk(base_path):
            for d in dirs:
                if d.startswith("Kramank_"):
                    kramank_folders.append(os.path.join(root, d))
        
        logger.info(f"Found {len(kramank_folders)} Kramank folders")
        
        # COST OPTIMIZATION: Limit batch processing
        if len(kramank_folders) > MAX_FOLDERS_TO_PROCESS:
            logger.warning(f"⚠️  COST PROTECTION: Found {len(kramank_folders)} folders. Processing only first {MAX_FOLDERS_TO_PROCESS} to control costs.")
            logger.warning(f"⚠️  To process more folders, increase MAX_FOLDERS_TO_PROCESS in main.py")
            kramank_folders = kramank_folders[:MAX_FOLDERS_TO_PROCESS]
        
        total_processed = 0
        total_errors = 0
        
        for i, folder in enumerate(kramank_folders, 1):
            try:
                logger.info(f"📁 Processing folder {i}/{len(kramank_folders)}: {folder}")
                # Run agent first
                agent_run(folder)
                
                # Generate PDFs after successful agent run
                generate_pdfs_for_folder(folder)
                
                total_processed += 1
                logger.info(f"✅ Successfully processed and generated PDFs for: {folder}")
                
                # COST OPTIMIZATION: Rate limiting between folder processing
                if i < len(kramank_folders):  # Don't sleep after last folder
                    import time
                    logger.info("⏱️  Rate limiting: waiting 5 seconds before next folder...")
                    time.sleep(5)
                    
            except Exception as e:
                total_errors += 1
                logger.error(f"❌ Error processing folder {folder}: {str(e)}")
                
                # COST OPTIMIZATION: Circuit breaker - stop if too many errors
                if total_errors >= 2:
                    logger.error("🚨 COST PROTECTION: Too many errors encountered. Stopping batch processing to prevent cost escalation.")
                    break
                    
                continue
        
        logger.info(f"📊 Batch processing completed: {total_processed} successful, {total_errors} errors")
        
    except Exception as e:
        logger.error(f"❌ Error in run_agent_on_all_kramank_folders: {str(e)}")


def generate_pdfs_for_folder(folder_path):
    """
    Generate PDFs for all debates processed from a specific folder
    """
    logger.info(f"Generating PDFs for debates from folder: {folder_path}")
    try:
        # Initialize PDF generator with output directory in the folder
        output_dir = "./generated_pdfs"
        # Use the folder path as the base path for images
        pdf_generator = PdfGenerater(output_dir=output_dir, image_base_path=folder_path)
        
        # Process all debates
        generated_pdfs = pdf_generator.process_all_pending_debates()
        
        if generated_pdfs:
            logger.info(f"✅ Successfully generated {len(generated_pdfs)} PDFs in {output_dir}")
            for pdf in generated_pdfs:
                logger.info(f"  📄 Generated: {pdf}")
        else:
            logger.warning(f"⚠️ No PDFs were generated for folder: {folder_path}")
            
    except Exception as e:
        logger.error(f"❌ Error generating PDFs for folder {folder_path}: {str(e)}")
        raise

def run_single_folder(folder_path):
    """
    Process a single Kramank folder safely and generate PDFs.
    COST OPTIMIZED: Use this for testing individual folders.
    """
    logger.info(f"Processing single folder: {folder_path}")
    try:
        # Run the agent first
        agent_run(folder_path)
        logger.info(f"✅ Successfully processed: {folder_path}")
        
        # Generate PDFs after successful processing
        generate_pdfs_for_folder(folder_path)
        
    except Exception as e:
        logger.error(f"❌ Error processing folder {folder_path}: {str(e)}")


if __name__ == "__main__":
    # create tables
    logger.info("🚀 Starting VidanBhavan processing with COST OPTIMIZATIONS")
    # createtables()
    run_agent_on_all_kramank_folders(r"D:\Test2000\2000")
                                     
    # folder_path = r"D:\Test2000\2000\MLA\Session_1_Budget\Kramank_1"
    
    # # COST OPTIMIZATION: Choose processing mode
    # logger.info("💡 COST-SAFE PROCESSING OPTIONS:")
    # logger.info("1. Single folder processing (RECOMMENDED for testing)")
    # logger.info("2. Batch processing (HIGH COST - disabled by default)")
    
    # # RECOMMENDED: Process single folder for testing
    # run_single_folder(folder_path)
    
    # COST WARNING: Batch processing can be expensive
    # logger.warning("🚨 Batch processing is currently DISABLED for cost protection")
    # logger.warning("🚨 To enable, set ENABLE_BATCH_PROCESSING = True and review costs")
    # run_agent_on_all_kramank_folders(folder_path)
    