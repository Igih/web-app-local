import os
import shutil
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def save_file(file, file_path: str):
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return True
    except Exception as e:
        logger.error(f"Error saving file to {file_path}: {str(e)}")
        raise