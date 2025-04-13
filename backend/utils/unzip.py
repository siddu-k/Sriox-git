import os
import zipfile
import shutil
import logging
from pathlib import Path

def extract_website(zip_file_path, subdomain):
    """
    Extract a website ZIP file to the static_sites folder
    
    Args:
        zip_file_path: Path to the uploaded ZIP file
        subdomain: The subdomain for the website
        
    Returns:
        dict: Success status and path information
    """
    # Define the destination directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    extract_path = os.path.join(base_dir, "static_sites", subdomain)
    
    try:
        # Create the directory if it doesn't exist
        os.makedirs(extract_path, exist_ok=True)
        
        # Clean any existing files
        for item in os.listdir(extract_path):
            item_path = os.path.join(extract_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        
        # Extract the ZIP file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Check for malicious paths (directory traversal)
            for file_name in zip_ref.namelist():
                target_path = os.path.join(extract_path, file_name)
                if not os.path.abspath(target_path).startswith(os.path.abspath(extract_path)):
                    raise ValueError(f"Security violation: Attempted path traversal with {file_name}")
            
            # Extract all files
            zip_ref.extractall(extract_path)
        
        # Clean up the temporary ZIP file
        os.remove(zip_file_path)
        
        logging.info(f"Successfully extracted website to {extract_path}")
        return {
            "success": True,
            "extract_path": extract_path,
            "relative_path": os.path.join("static_sites", subdomain)
        }
    
    except zipfile.BadZipFile:
        logging.error(f"Invalid ZIP file: {zip_file_path}")
        return {
            "success": False,
            "error": "Invalid ZIP file"
        }
    except ValueError as e:
        logging.error(str(e))
        return {
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logging.error(f"Error extracting ZIP file: {str(e)}")
        return {
            "success": False,
            "error": f"Error extracting ZIP file: {str(e)}"
        }

def delete_website_folder(subdomain):
    """
    Delete a website folder from static_sites
    
    Args:
        subdomain: The subdomain of the website to delete
        
    Returns:
        bool: Success status
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        folder_path = os.path.join(base_dir, "static_sites", subdomain)
        
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            logging.info(f"Deleted website folder: {folder_path}")
            return True
        else:
            logging.warning(f"Website folder not found: {folder_path}")
            return False
    except Exception as e:
        logging.error(f"Error deleting website folder: {str(e)}")
        return False