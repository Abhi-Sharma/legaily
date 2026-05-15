import pytesseract
from PIL import Image
import pdfplumber
import io

async def extract_text(file):
    """
    Extract text from different file types
    
    :param file: FastAPI UploadFile object
    :return: Extracted text
    """
    # Read file content
    content = await file.read()
    
    # Determine file type from filename
    file_extension = file.filename.split('.')[-1].lower()
    
    # Reset file pointer for future reads
    await file.seek(0)
    
    # Process based on file type
    if file_extension == 'pdf':
        # Use pdfplumber for PDFs with a hybrid OCR fallback
        extracted_pages = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                
                # Heuristic: If page text is very short/empty, it's likely a scan
                if not page_text or len(page_text.strip()) < 50:
                    try:
                        # Convert page to image and OCR it
                        img = page.to_image(resolution=200).original
                        page_text = pytesseract.image_to_string(img)
                    except Exception as e:
                        print(f"OCR fallback failed for a page: {e}")
                        
                extracted_pages.append(page_text or "")
        
        return "\n".join(extracted_pages)
    
    elif file_extension in ['jpg', 'jpeg', 'png']:
        # Use pytesseract for images
        try:
            image = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(image)
        except Exception as e:
            return f"Error processing image: {str(e)}"
    
    else:
        # For text files, just decode the content
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # Try another common encoding if utf-8 fails
            try:
                return content.decode('latin-1')
            except:
                return "Could not decode file content"