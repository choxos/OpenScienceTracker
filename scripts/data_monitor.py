#!/usr/bin/env python3
import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import django

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ost_web.settings')
django.setup()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ost/logs/data_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataFileHandler(FileSystemEventHandler):
    def __init__(self, file_type, command_name):
        self.file_type = file_type
        self.command_name = command_name
        self.processing_files = set()  # Track files being processed
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self.should_process_file(file_path):
            logger.info(f"New {self.file_type} file detected: {file_path}")
            # Wait a moment for file to be fully written
            time.sleep(5)
            self.process_file(file_path)
    
    def on_moved(self, event):
        if event.is_directory:
            return
        
        file_path = event.dest_path
        if self.should_process_file(file_path):
            logger.info(f"New {self.file_type} file moved: {file_path}")
            time.sleep(2)
            self.process_file(file_path)
    
    def should_process_file(self, file_path):
        """Check if file should be processed"""
        if not file_path.endswith('.csv'):
            return False
        
        filename = os.path.basename(file_path)
        
        if self.file_type == 'EPMC':
            return filename.startswith('epmc_') or filename.startswith('epmc_db_')
        elif self.file_type == 'transparency':
            return filename.startswith('transparency_')
        
        return False
    
    def process_file(self, file_path):
        """Process the detected file"""
        if file_path in self.processing_files:
            logger.info(f"File {file_path} is already being processed, skipping")
            return
        
        try:
            self.processing_files.add(file_path)
            
            # Check if file is complete (no longer being written to)
            if not self.is_file_complete(file_path):
                logger.info(f"File {file_path} is still being written, waiting...")
                time.sleep(10)
                if not self.is_file_complete(file_path):
                    logger.warning(f"File {file_path} may still be incomplete, processing anyway")
            
            # Run Django management command
            logger.info(f"Processing {file_path} with command: {self.command_name}")
            
            cmd = [
                '/home/ost/applications/OpenScienceTracker/ost_env/bin/python',
                '/home/ost/applications/OpenScienceTracker/manage.py',
                self.command_name,
                '--file', file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd='/home/ost/applications/OpenScienceTracker'
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully processed {file_path}")
                logger.info(f"Command output: {result.stdout}")
                
                # Move processed file to archive directory
                self.archive_file(file_path)
            else:
                logger.error(f"Error processing {file_path}: {result.stderr}")
            
        except Exception as e:
            logger.error(f"Exception processing {file_path}: {str(e)}")
        finally:
            self.processing_files.discard(file_path)
    
    def is_file_complete(self, file_path):
        """Check if file is complete by comparing sizes over time"""
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(2)
            size2 = os.path.getsize(file_path)
            return size1 == size2
        except OSError:
            return False
    
    def archive_file(self, file_path):
        """Move processed file to archive directory"""
        try:
            archive_dir = os.path.join(os.path.dirname(file_path), 'processed')
            os.makedirs(archive_dir, exist_ok=True)
            
            filename = os.path.basename(file_path)
            archive_path = os.path.join(archive_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
            
            os.rename(file_path, archive_path)
            logger.info(f"Archived {file_path} to {archive_path}")
        except Exception as e:
            logger.error(f"Error archiving {file_path}: {str(e)}")

def main():
    # Directories to monitor
    epmc_dir = '/home/ost/data/epmc_monthly_data'
    transparency_dir = '/home/ost/data/transparency_results'
    
    # Create directories if they don't exist
    os.makedirs(epmc_dir, exist_ok=True)
    os.makedirs(transparency_dir, exist_ok=True)
    
    # Create event handlers
    epmc_handler = DataFileHandler('EPMC', 'process_epmc_files')
    transparency_handler = DataFileHandler('transparency', 'process_transparency_files')
    
    # Create observer
    observer = Observer()
    observer.schedule(epmc_handler, epmc_dir, recursive=False)
    observer.schedule(transparency_handler, transparency_dir, recursive=False)
    
    # Start monitoring
    observer.start()
    logger.info("Data file monitoring started")
    logger.info(f"Monitoring EPMC files in: {epmc_dir}")
    logger.info(f"Monitoring transparency files in: {transparency_dir}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Data file monitoring stopped")
    
    observer.join()

if __name__ == "__main__":
    main() 