# Medical-assistance-using-OCR
This Medical Assistance project uses OCR with Python, Tesseract, and OpenCV to extract data from medical  documents and is deployed using Flask with MongoDB or SQLite for storage. 
Purpose of the Project
This system is designed to help users (patients or healthcare workers) extract meaningful medical information—such as medications, dosages, lab tests, and vitals—from images of medical documents (like prescriptions, reports, or handwritten notes).
Key Components and Workflow
1. OCR Processing (ocr_processor.py)
Uses Tesseract OCR via pytesseract to extract text from medical document images.
Applies image preprocessing using OpenCV and PIL to improve OCR accuracy:
Grayscale conversion
Adaptive thresholding
Noise reduction (bilateral filter)
Contrast enhancement (CLAHE)
Dilation
Supports multiple OCR modes (--psm, --oem) for better extraction reliability.
2. Medical Entity Recognition (medical_terms.json)
This file provides dictionaries/lists of:
Medications (e.g., acetaminophen, ibuprofen, amoxicillin)
Dosage forms/frequencies (e.g., mg, tablet, twice daily)
Lab test names (e.g., WBC, Hemoglobin, TSH)
Vital signs (e.g., BP, heart rate, BMI)
Common abbreviations (e.g., q.d. = once daily, NPO = nothing by mouth)
This reference data is used to match and identify recognized terms in the OCR output, enabling medical context extraction.
3. User and Document Models (models.py)
Defines two key database models using SQLAlchemy:
User: To manage user accounts (email, password, etc.)
Document: Stores:
Raw OCR text
Processed structured data (JSON with extracted medical terms)
Encoded image data
Document type (prescription, lab report, etc.)
This allows users to upload, view, and store medical documents securely.
