"""
SilentHUD - OCR Pipeline
Captures screen regions and extracts text using Tesseract OCR.
"""

from PIL import Image, ImageGrab, ImageEnhance, ImageFilter
import pytesseract
from typing import Optional, Tuple
import io


def get_cursor_position() -> Tuple[int, int]:
    """
    Get current mouse cursor position.
    Uses PyQt6 for cross-platform compatibility.
    """
    from PyQt6.QtGui import QCursor
    pos = QCursor.pos()
    return pos.x(), pos.y()


def capture_region(
    center_x: int, 
    center_y: int, 
    width: int = 400, 
    height: int = 200
) -> Image.Image:
    """
    Capture a screen region centered on the given coordinates.
    
    Args:
        center_x: X coordinate of region center
        center_y: Y coordinate of region center
        width: Width of capture region
        height: Height of capture region
        
    Returns:
        PIL Image of the captured region
    """
    # Calculate bounding box
    left = max(0, center_x - width // 2)
    top = max(0, center_y - height // 2)
    right = left + width
    bottom = top + height
    
    # Capture the region
    screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
    return screenshot


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR accuracy.
    
    Args:
        image: Input PIL Image
        
    Returns:
        Preprocessed PIL Image
    """
    # Convert to grayscale
    gray = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(2.0)
    
    # Scale up for better OCR (Tesseract works better with larger images)
    width, height = contrasted.size
    scaled = contrasted.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    
    # Sharpen
    sharpened = scaled.filter(ImageFilter.SHARPEN)
    
    return sharpened


def extract_text(image: Image.Image, preprocess: bool = True) -> str:
    """
    Extract text from an image using Tesseract OCR.
    
    Args:
        image: PIL Image to process
        preprocess: Whether to apply preprocessing for better accuracy
        
    Returns:
        Extracted text string
    """
    if preprocess:
        image = preprocess_image(image)
    
    # Tesseract configuration for better accuracy
    # --psm 6: Assume uniform block of text
    # --oem 3: Use LSTM neural network mode
    config = '--psm 6 --oem 3'
    
    text = pytesseract.image_to_string(image, config=config)
    
    # Clean up the text
    text = text.strip()
    
    return text


def capture_and_ocr(
    width: int = 400, 
    height: int = 200,
    expand_on_empty: bool = True,
    image: Optional[Image.Image] = None
) -> str:
    """
    Capture screen region at cursor position and extract text.
    
    Args:
        width: Capture region width
        height: Capture region height
        expand_on_empty: If True and no text found, try larger region
        image: Optional pre-captured image to use instead of capturing
        
    Returns:
        Extracted text or empty string if none found
    """
    if image:
        screenshot = image
    else:
        # Get cursor position and capture
        x, y = get_cursor_position()
        screenshot = capture_region(x, y, width, height)
    
    text = extract_text(screenshot)
    
    # If no text found and expand enabled, try larger region
    # Note: If image is provided, we can't easily expand unless we recapture,
    # so we skip expansion if image is provided.
    if not text and expand_on_empty and not image:
        screenshot = capture_region(x, y, width * 2, height * 2)
        text = extract_text(screenshot)
    
    return text


def capture_full_screen_ocr() -> str:
    """
    Capture and OCR the entire screen.
    Useful for capturing full questions or content.
    
    Returns:
        Extracted text from full screen
    """
    screenshot = ImageGrab.grab()
    text = extract_text(screenshot, preprocess=False)  # Skip preprocessing for large images
    return text
