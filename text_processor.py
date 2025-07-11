import re
import json
import os
import logging
import spacy
from datetime import datetime

logger = logging.getLogger(__name__)

# Load medical terminology
try:
    with open('medical_terms.json', 'r') as f:
        MEDICAL_TERMS = json.load(f)
except FileNotFoundError:
    # If file doesn't exist, create a basic version
    MEDICAL_TERMS = {
        "medications": [],
        "common_dosages": ["mg", "mcg", "ml", "g", "tablet", "capsule", "injection", "daily", "twice daily", "three times daily"],
        "lab_test_names": [],
        "vital_signs": ["BP", "blood pressure", "heart rate", "pulse", "temperature", "respiratory rate", "SpO2", "oxygen saturation"],
        "medical_abbreviations": {
            "qd": "once daily",
            "bid": "twice daily",
            "tid": "three times daily",
            "qid": "four times daily",
            "prn": "as needed",
            "po": "by mouth",
            "sc": "subcutaneous",
            "im": "intramuscular",
            "iv": "intravenous"
        }
    }
    # Save the basic version
    with open('medical_terms.json', 'w') as f:
        json.dump(MEDICAL_TERMS, f, indent=2)

# Initialize spaCy if available
try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    SPACY_AVAILABLE = False
    logger.warning("spaCy model not available. Using regex-based extraction only.")

def extract_dates(text):
    """Extract dates from text using regex patterns"""
    # Various date formats
    date_patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
        r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YYYY or DD-MM-YYYY
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
        r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',  # DD Month YYYY
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(matches)
    
    return dates

def extract_medications(text):
    """Extract medication names and dosages"""
    medications = []
    
    # Check for common medication names from our database
    for med in MEDICAL_TERMS.get("medications", []):
        if re.search(r'\b' + re.escape(med) + r'\b', text, re.IGNORECASE):
            medications.append(med)
    
    # Look for patterns like "X mg" or "X tablet(s)"
    dosage_pattern = r'\b\w+\s+\d+\s*(?:' + '|'.join(MEDICAL_TERMS.get("common_dosages", [])) + r')\b'
    dosage_matches = re.findall(dosage_pattern, text, re.IGNORECASE)
    medications.extend(dosage_matches)
    
    # Use spaCy if available
    if SPACY_AVAILABLE:
        doc = nlp(text)
        
        # Look for PROPN (proper noun) entities that might be medications
        potential_meds = [ent.text for ent in doc.ents if ent.label_ == "PRODUCT"]
        medications.extend(potential_meds)
    
    return list(set(medications))  # Remove duplicates

def extract_doctor_info(text):
    """Extract doctor name and information"""
    doctor_info = {}
    
    # Look for "Dr." or "Doctor" followed by a name
    doctor_patterns = [
        r'(?:Dr\.|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
        r'(?:Physician|Provider):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})'
    ]
    
    for pattern in doctor_patterns:
        match = re.search(pattern, text)
        if match:
            doctor_info["name"] = match.group(1)
            break
    
    # Look for phone numbers
    phone_pattern = r'(?:Phone|Tel|Contact)(?::|number)?[:\s]*(\(\d{3}\)\s*\d{3}-\d{4}|\d{3}[-.\s]\d{3}[-.\s]\d{4}|\d{10})'
    phone_match = re.search(phone_pattern, text, re.IGNORECASE)
    if phone_match:
        doctor_info["phone"] = phone_match.group(1)
    
    return doctor_info

def extract_patient_info(text):
    """Extract patient information"""
    patient_info = {}
    
    # Look for patient name
    name_patterns = [
        r'(?:Patient|Name):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
        r'(?:Patient|Name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info["name"] = match.group(1)
            break
    
    # Look for dates of birth
    dob_patterns = [
        r'(?:DOB|Date of Birth)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(?:Born|Birth)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
    ]
    
    for pattern in dob_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info["dob"] = match.group(1)
            break
    
    # Look for patient ID
    id_patterns = [
        r'(?:ID|Patient ID|MRN)[:\s]*([A-Z0-9-]+)',
        r'(?:Medical Record Number)[:\s]*([A-Z0-9-]+)'
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info["id"] = match.group(1)
            break
    
    return patient_info

def extract_lab_results(text):
    """Extract lab test results"""
    lab_results = []
    
    # Look for patterns like "Test Name: XX.X unit" or "Test Name XX.X unit"
    result_pattern = r'([A-Za-z\s]+):\s*(\d+\.?\d*)\s*([A-Za-z/%]+)'
    matches = re.findall(result_pattern, text)
    
    for match in matches:
        test_name, value, unit = match
        lab_results.append({
            "test": test_name.strip(),
            "value": value,
            "unit": unit
        })
    
    # Look for common lab test names
    for test_name in MEDICAL_TERMS.get("lab_test_names", []):
        if test_name.lower() in text.lower():
            # Find the value after the test name
            value_pattern = fr'{re.escape(test_name)}[:\s]*(\d+\.?\d*)\s*([A-Za-z/%]+)'
            value_match = re.search(value_pattern, text, re.IGNORECASE)
            
            if value_match:
                lab_results.append({
                    "test": test_name,
                    "value": value_match.group(1),
                    "unit": value_match.group(2)
                })
    
    return lab_results

def extract_instructions(text):
    """Extract medication instructions or physician instructions"""
    instructions = []
    
    # Look for common instructional phrases
    instruction_patterns = [
        r'(?:Take|Use|Apply)[^.;]+(daily|twice daily|three times daily|every \d+ hours)[^.;]+',
        r'Instructions?:[^.;]+',
        r'Directions?:[^.;]+'
    ]
    
    for pattern in instruction_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        instructions.extend(matches)
    
    # Check for medication abbreviations and replace with full text
    for abbr, full_text in MEDICAL_TERMS.get("medical_abbreviations", {}).items():
        abbr_pattern = r'\b' + re.escape(abbr) + r'\b'
        if re.search(abbr_pattern, text, re.IGNORECASE):
            instructions.append(f"{abbr} ({full_text})")
    
    return instructions

def extract_diagnoses(text):
    """Extract diagnoses or conditions"""
    diagnoses = []
    
    # Look for diagnosis sections
    diagnosis_patterns = [
        r'Diagnosis(?:es)?:[^.;]+',
        r'Assessment:[^.;]+',
        r'Condition(?:s)?:[^.;]+'
    ]
    
    for pattern in diagnosis_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        diagnoses.extend(matches)
    
    # If we have spaCy, try to extract medical conditions
    if SPACY_AVAILABLE:
        doc = nlp(text)
        
        # Look for entities that might be medical conditions
        for ent in doc.ents:
            if ent.label_ in ["DISEASE", "CONDITION"]:
                diagnoses.append(ent.text)
    
    return diagnoses

def extract_medical_entities(text, document_type):
    """
    Extract medical entities from OCR text based on document type.
    
    Args:
        text: The OCR-extracted text
        document_type: Type of medical document (prescription, lab_report, etc.)
        
    Returns:
        Dictionary of extracted medical entities
    """
    try:
        logger.debug(f"Processing text as {document_type}")
        
        # Common extractions for all document types
        results = {
            "dates": extract_dates(text),
            "patient_info": extract_patient_info(text)
        }
        
        # Document-specific extractions
        if document_type == "prescription":
            results.update({
                "medications": extract_medications(text),
                "doctor_info": extract_doctor_info(text),
                "instructions": extract_instructions(text)
            })
        
        elif document_type == "lab_report":
            results.update({
                "lab_results": extract_lab_results(text),
                "doctor_info": extract_doctor_info(text)
            })
        
        elif document_type == "medical_note":
            results.update({
                "diagnoses": extract_diagnoses(text),
                "doctor_info": extract_doctor_info(text),
                "medications": extract_medications(text)
            })
        
        else:  # For any other document type, extract everything
            results.update({
                "medications": extract_medications(text),
                "doctor_info": extract_doctor_info(text),
                "instructions": extract_instructions(text),
                "lab_results": extract_lab_results(text),
                "diagnoses": extract_diagnoses(text)
            })
        
        # Remove empty lists or dictionaries
        results = {k: v for k, v in results.items() if v}
        
        return results
    
    except Exception as e:
        logger.error(f"Error extracting medical entities: {str(e)}")
        # Return at least the raw text if processing fails
        return {"raw_text": text}
