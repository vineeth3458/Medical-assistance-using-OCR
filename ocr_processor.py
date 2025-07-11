import cv2
import numpy as np
import pytesseract
import logging
from PIL import Image
import io
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set Tesseract configuration
if not os.environ.get('TESSDATA_PREFIX'):
    # Try to set TESSDATA_PREFIX to common locations
    for possible_path in ['/usr/share/tessdata', '/usr/local/share/tessdata', 
                          '/opt/homebrew/share/tessdata', './tessdata']:
        if os.path.exists(possible_path):
            os.environ['TESSDATA_PREFIX'] = possible_path
            logger.info(f"Set TESSDATA_PREFIX to {possible_path}")
            break

def preprocess_image(image_data):
    """
    Preprocess the image for better OCR results.
    
    Args:
        image_data: The binary image data
        
    Returns:
        Preprocessed image as a numpy array
    """
    try:
        # Convert binary data to numpy array
        nparr = np.frombuffer(image_data, np.uint8)
        
        # Decode image
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image data")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding instead of global thresholding
        # This handles varying illumination better
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(adaptive_thresh, 9, 75, 75)
        
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply dilation to make text more clear
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(filtered, kernel, iterations=1)
        
        # Create a PIL Image from the processed image for better compatibility with pytesseract
        pil_image = Image.fromarray(dilated)
        
        return pil_image
    except Exception as e:
        logger.error(f"Error preprocessing image: {str(e)}")
        # If there's an error in preprocessing, try to return the original image
        try:
            image = Image.open(io.BytesIO(image_data))
            logger.info("Falling back to original image without preprocessing")
            return image
        except Exception as fallback_e:
            logger.error(f"Fallback to original image failed: {str(fallback_e)}")
            raise Exception("Failed to process the image")

def process_image(image_data):
    """
    Process the image with OCR to extract text.
    
    Args:
        image_data: The binary image data
        
    Returns:
        Extracted text from the image
    """
    try:
        # Preprocess the image
        processed_image = preprocess_image(image_data)
        
        # Try multiple Tesseract configurations for best results
        all_text = ""
        
        # Try with different PSM (Page Segmentation Modes)
        for psm in [4, 6, 3, 1]:
            # For PSM modes:
            # 1 = Auto OSD
            # 3 = Fully automatic page segmentation, but no OSD (default)
            # 4 = Assume a single column of text of variable sizes
            # 6 = Assume a single uniform block of text
            
            for oem in [1, 3]:
                # For OEM modes:
                # 1 = Neural nets LSTM engine only
                # 3 = Default, based on what is available
                
                custom_config = f'--oem {oem} --psm {psm}'
                
                try:
                    logger.debug(f"Trying OCR with config: {custom_config}")
                    text = pytesseract.image_to_string(processed_image, config=custom_config)
                    
                    # If we got meaningful text, add it to our results
                    if text and not text.isspace() and len(text.strip()) > 10:
                        all_text = text
                        logger.debug(f"Successful extraction with config: {custom_config}")
                        break
                except Exception as config_error:
                    logger.warning(f"OCR attempt failed with config {custom_config}: {str(config_error)}")
            
            # If we have good text, stop trying configurations
            if all_text:
                break
        
        # If all OCR attempts failed, try one more time with default settings
        if not all_text:
            logger.warning("All configured OCR attempts failed, trying default settings")
            try:
                all_text = pytesseract.image_to_string(processed_image)
            except Exception as e:
                logger.error(f"Default OCR attempt failed: {str(e)}")
                
        logger.debug(f"Extracted text: {all_text[:100]}...")
        return all_text or "No text could be extracted from the image."
    except Exception as e:
        logger.error(f"Error in OCR processing: {str(e)}")
        raise Exception(f"OCR processing failed: {str(e)}")
