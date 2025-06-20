import requests
import cv2
import numpy as np
from typing import Dict, Any, Optional
import easyocr
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        # Initialize EasyOCR reader for Vietnamese and English
        self.reader = easyocr.Reader(['vi', 'en'])
        
    def extract_vietnamese_id_info(self, image_path: str) -> Dict[str, Any]:
        """Extract information from Vietnamese ID card"""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not read image")
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.equalizeHist(gray)
            
            # Extract text using EasyOCR
            results = self.reader.readtext(enhanced)
            
            # Combine all detected text
            text_lines = [result[1] for result in results]
            full_text = " ".join(text_lines)
            
            # Extract specific fields using regex patterns
            extracted_data = self._parse_vietnamese_id_text(full_text, text_lines)
            
            # Calculate confidence score
            confidence_scores = [result[2] for result in results]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            extracted_data['ocr_confidence'] = avg_confidence
            extracted_data['processing_timestamp'] = datetime.utcnow().isoformat()
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return {
                'error': str(e),
                'ocr_confidence': 0,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    def _parse_vietnamese_id_text(self, full_text: str, text_lines: list) -> Dict[str, Any]:
        """Parse Vietnamese ID text to extract structured information"""
        result = {}
        
        # Patterns for Vietnamese ID fields
        patterns = {
            'id_number': r'(\d{9}|\d{12})',
            'full_name': r'(?:Họ và tên|Tên|Name)[:\s]*([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ\s]+)',
            'dob': r'(?:Ngày sinh|Sinh|Date of birth)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            'address': r'(?:Nơi thường trú|Địa chỉ|Address)[:\s]*([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ\s,0-9/-]+)',
            'sex': r'(?:Giới tính|Sex)[:\s]*([MFNamNữ]+)',
            'nationality': r'(?:Quốc tịch|Nationality)[:\s]*([A-Za-z\s]+)',
            'expiry_date': r'(?:Có giá trị đến|Valid until)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})'
        }
        
        # Extract using patterns
        for field, pattern in patterns.items():
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip()
        
        # Additional validation and cleaning
        if 'dob' in result:
            result['dob'] = self._normalize_date(result['dob'])
        
        if 'full_name' in result:
            result['full_name'] = result['full_name'].title()
        
        # Validate ID number format
        if 'id_number' in result:
            if not (len(result['id_number']) == 9 or len(result['id_number']) == 12):
                result['id_number_valid'] = False
            else:
                result['id_number_valid'] = True
        
        return result
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date format to DD/MM/YYYY"""
        # Replace various separators with /
        normalized = re.sub(r'[-.]', '/', date_str)
        return normalized
    
    def verify_document_authenticity(self, image_path: str) -> Dict[str, Any]:
        """Basic document authenticity checks"""
        try:
            image = cv2.imread(image_path)
            
            # Check image quality
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate sharpness using Laplacian variance
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Check for security features (simplified)
            # In real implementation, check for watermarks, holograms, etc.
            
            # Color analysis for authenticity
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            return {
                'sharpness_score': float(sharpness),
                'quality_check': sharpness > 100,  # Threshold for acceptable quality
                'authenticity_score': min(sharpness / 500, 1.0),  # Normalized score
                'security_features_detected': sharpness > 200  # Simplified check
            }
            
        except Exception as e:
            logger.error(f"Document verification failed: {str(e)}")
            return {
                'error': str(e),
                'authenticity_score': 0,
                'quality_check': False
            }

# Legacy function for backward compatibility
def extract_vn_id_data(image_path: str) -> Dict:
    """Legacy function - use OCRService.extract_vietnamese_id_info instead"""
    ocr_service = OCRService()
    return ocr_service.extract_vietnamese_id_info(image_path) 