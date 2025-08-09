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

Features
Document Upload & Management
Upload and manage different types of documents with search and categorization.

OCR Processing
Extract text from images and scanned PDFs using Tesseract OCR (tessdata/eng.traineddata).

Text Processing
Includes keyword extraction, medical term recognition (medical_terms.json), and content analysis.

User Interface
HTML templates for viewing documents, profiles, and search results (templates/ folder).

Frontend Enhancements
JavaScript and CSS for camera-based uploads and improved UI (static/ folder).
Project Structure
graphql
Copy
Edit
TeacherMediaHub/
├── app.py                 # Flask app initialization and routes
├── main.py                # Entry point for running the application
├── document_manager.py    # Handles document storage, retrieval, and metadata
├── ocr_processor.py       # OCR extraction logic using Tesseract
├── text_processor.py      # Text cleaning, keyword extraction, etc.
├── models.py              # Database models (SQLAlchemy or similar)
├── medical_terms.json     # Predefined terms for recognition
├── static/                # CSS and JavaScript assets
├── templates/             # HTML templates for the UI
├── tessdata/              # Tesseract language data
├── pyproject.toml         # Project dependencies and metadata
├── uv.lock                # Dependency lock file
└── generated-icon.png     # App icon/logo
Requirements
Python 3.8+

Flask

SQLAlchemy

Tesseract OCR

Pillow

Other dependencies listed in pyproject.toml

Installation
Clone the repository

bash
Copy
Edit
git clone <repo-url>
cd TeacherMediaHub
Install dependencies

bash
Copy
Edit
pip install -r requirements.txt
(Or use pip install . if using Poetry/pyproject.toml)

Install Tesseract OCR

Linux (Debian/Ubuntu): sudo apt install tesseract-ocr

Windows: Download from Tesseract GitHub

Run the app

bash
Copy
Edit
python main.py
Usage
Access the app via: http://127.0.0.1:5000

Upload documents/images.

Process with OCR.

View and search extracted content.

