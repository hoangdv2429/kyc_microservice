import requests
import cv2
import numpy as np
from typing import Dict, Any, Optional
import easyocr
import re
from datetime import datetime
import logging
from PIL import Image

# Fix for PIL.Image.ANTIALIAS deprecation
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
if not hasattr(Image, 'BICUBIC'):
    Image.BICUBIC = Image.BICUBIC
if not hasattr(Image, 'NEAREST'):
    Image.NEAREST = Image.NEAREST

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        # Initialize EasyOCR reader for Vietnamese and English
        self.reader = easyocr.Reader(['vi', 'en'])
        
    def extract_vietnamese_id_front(self, image_path: str) -> Dict[str, Any]:
        """Extract information from Vietnamese ID card front side"""
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
            
            # Extract specific fields using regex patterns for front side
            extracted_data = self._parse_vietnamese_id_front_text(full_text, text_lines)
            
            # Calculate confidence score
            confidence_scores = [result[2] for result in results]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            extracted_data['ocr_confidence'] = avg_confidence
            extracted_data['processing_timestamp'] = datetime.utcnow().isoformat()
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"OCR extraction failed for front: {str(e)}")
            return {
                'error': str(e),
                'ocr_confidence': 0,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    def extract_vietnamese_id_back(self, image_path: str) -> Dict[str, Any]:
        """Extract information from Vietnamese ID card back side"""
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
            
            # Extract specific fields using regex patterns for back side
            extracted_data = self._parse_vietnamese_id_back_text(full_text, text_lines)
            
            # Calculate confidence score
            confidence_scores = [result[2] for result in results]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            extracted_data['ocr_confidence'] = avg_confidence
            extracted_data['processing_timestamp'] = datetime.utcnow().isoformat()
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"OCR extraction failed for back: {str(e)}")
            return {
                'error': str(e),
                'ocr_confidence': 0,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    def extract_vietnamese_id_info(self, image_path: str) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        Defaults to front side processing.
        """
        logger.warning("Using deprecated extract_vietnamese_id_info method. Consider using extract_vietnamese_id_front or extract_vietnamese_id_back.")
        return self.extract_vietnamese_id_front(image_path)
    
    def _parse_vietnamese_id_front_text(self, full_text: str, text_lines: list) -> Dict[str, Any]:
        """Parse Vietnamese ID front text to extract structured information"""
        result = {}
        
        # Debug: Log the extracted text for troubleshooting
        logger.info(f"OCR Front Text: {full_text}")
        logger.info(f"OCR Front Lines: {text_lines}")
        
        # More flexible patterns for Vietnamese ID front side fields
        patterns = {
            # ID number - try multiple variations
            'id_number': [
                r'(?:Số|No\.|ID|CCCD|CMND)[:\s]*(\d{12})(?!\d)',  # Original
                r'(\d{12})(?!\d)',  # Just 12 digits anywhere
                r'(?:CCCD|CMND)[:\s]*(\d{9,12})',  # 9-12 digits after CCCD/CMND
            ],
            
            # Name - more flexible patterns
            'full_name': [
                r'(?:Họ và tên|Full name)[:\s]*([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỬỮỰÝỲỶỸỴĐ\s]+?)(?=\s*(?:Ngày sinh|Date of birth|Giới tính|Sex|\n|$))',
                r'([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỬỮỰÝỲỶỸỴĐ]{2,}\s+[A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỬỮỰÝỲỶỸỴĐ\s]+)',  # Vietnamese name pattern
            ],
            
            # Date of birth - multiple formats
            'dob': [
                r'(?:Ngày sinh|Date of birth|Sinh)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
                r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',  # Any date pattern
            ],
            
            # Gender - flexible
            'sex': [
                r'(?:Giới tính|Sex)[:\s]*([MFNamNữ]+)',
                r'\b(Nam|Nữ|M|F)\b',  # Just the gender words
            ],
            
            # Nationality
            'nationality': [
                r'(?:Quốc tịch|Nationality)[:\s]*([A-Za-z\s]+)',
                r'\b(Việt Nam|Vietnam|VN|Vi)\b',  # Common nationality values
            ],
            
            # Place of origin
            'place_of_origin': [
                r'(?:Quê quán|Place of origin)[:\s]*([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỬỮỰÝỲỶỸỴĐ\s,0-9/-]+?)(?=\s*(?:Nơi thường trú|Place of residence|Có giá trị|Date of expiry|\n|$))',
            ],
            
            # Place of residence
            'place_of_residence': [
                r'(?:Nơi thường trú|Place of residence)[:\s]*([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỬỮỰÝỲỶỸỴĐ\s,0-9/-]+?)(?=\s*(?:Có giá trị|Date of expiry|\n|$))',
            ],
            
            # Expiry date
            'expiry_date': [
                r'(?:Có giá trị|Date of expiry|Expiry)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            ],
        }
        
        # Extract using patterns with fallbacks
        for field, pattern_list in patterns.items():
            if isinstance(pattern_list, str):
                pattern_list = [pattern_list]
                
            for pattern in pattern_list:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    logger.info(f"Extracted {field}: {result[field]}")
                    break  # Stop after first successful match
        
        # Post-processing and validation
        if 'dob' in result:
            result['dob'] = self._normalize_date(result['dob'])
        
        if 'expiry_date' in result:
            result['expiry_date'] = self._normalize_date(result['expiry_date'])
        
        if 'full_name' in result:
            # Clean up the name field
            name = result['full_name'].strip()
            # Remove any trailing text that might have been captured
            name = re.sub(r'\s*(?:ngày sinh|sinh|date of birth).*$', '', name, flags=re.IGNORECASE)
            result['full_name'] = name.title()
        
        # Clean up place fields
        for field in ['place_of_origin', 'place_of_residence']:
            if field in result:
                result[field] = result[field].strip()
        
        # Validate ID number
        if 'id_number' in result:
            id_num = result['id_number']
            if len(id_num) == 12 and id_num.isdigit():
                result['id_number_valid'] = True
            else:
                result['id_number_valid'] = False
        
        logger.info(f"Final extracted front data: {result}")
        return result
    
    def _parse_vietnamese_id_back_text(self, full_text: str, text_lines: list) -> Dict[str, Any]:
        """Parse Vietnamese ID back text to extract structured information"""
        result = {}
        
        # Debug: Log the extracted text for troubleshooting
        logger.info(f"OCR Back Text: {full_text}")
        logger.info(f"OCR Back Lines: {text_lines}")
        
        # More flexible patterns for Vietnamese ID back side fields
        patterns = {
            # Personal identification features
            'personal_identification': [
                r'(?:Đặc điểm nhận dạng|Personal identification)[:\s]*(.+?)(?=\s*(?:Ngày|Date))',  # Stop at "Ngày" or "Date"
                r'(?:Seo|Vết|Nốt|Không có|None|Khuyết|Bớt)[^.]*[.:]?[^.]*(?:[.:]|$)',  # Common personal ID patterns
            ],
            
            # Issue date - multiple patterns
            'issue_date': [
                r'(?:ngày, tháng, năm|Date, month, year)[:\s]*(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})',
                r'(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})',  # Any date pattern
            ],
            
            # Issuing authority
            'issuing_authority': [
                r'(?:Nơi cấp|Issued by|Cơ quan cấp)[:\s]*([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ\s,0-9/-]+?)(?=\s*(?:ngày|Date|\n|$))',
                r'(Cảnh sát [A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ\s]+)',  # Common pattern
                r'(Cục [A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ\s]+)',  # Department pattern
            ],
        }
        
        # Extract using patterns with fallbacks
        for field, pattern_list in patterns.items():
            if isinstance(pattern_list, str):
                pattern_list = [pattern_list]
                
            for pattern in pattern_list:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    result[field] = match.group(1).strip()
                    logger.info(f"Extracted {field}: {result[field]}")
                    break  # Stop after first successful match
        
        # Extract MRZ (Machine Readable Zone)
        mrz_data = self._extract_mrz(full_text, text_lines)
        if mrz_data:
            result['mrz'] = mrz_data
            logger.info(f"Extracted MRZ data: {mrz_data}")
        
        # Post-processing
        if 'issue_date' in result:
            result['issue_date'] = self._normalize_date(result['issue_date'])
        
        if 'personal_identification' in result:
            # Clean up personal identification field
            personal_id = result['personal_identification'].strip()
            # Remove any trailing unwanted text
            personal_id = re.sub(r'\s*(?:ngày, tháng, năm|Date, month, year).*$', '', personal_id, flags=re.IGNORECASE)
            result['personal_identification'] = personal_id
        
        logger.info(f"Final extracted back data: {result}")
        return result
    
    def _parse_mrz_data(self, line1: str, line2: str, line3: str) -> Dict[str, Any]:
        """Parse Machine Readable Zone (MRZ) data for Vietnamese ID format (TD1 format)
        
        Vietnamese ID MRZ format (ICAO TD1 - 30 characters per line):
        Line 1: IDVNM<document_last_9_digits><check_digit><12_digits_document_number>
        Line 2: <birth_date><check_digit><sex><expiry_date><check_digit><nationality><<<<<<<<<<optional_X>
        Line 3: <family_names><<<GIVEN_NAMES_1><<GIVEN_NAMES_2><<<<<<<<<<<<<<
        
        Check digit calculation uses the 7,3,1 rule with values:
        0-9: face value, A-Z: 10-35, '<' (filler): 0
        """
        mrz_data = {}
        
        try:
            # Validate line lengths (TD1 format - 30 characters each)
            if len(line1) != 30 or len(line2) != 30 or len(line3) != 30:
                logger.warning(f"Invalid MRZ line lengths: {len(line1)}, {len(line2)}, {len(line3)} (expected 30 each)")
                return mrz_data
            
            # Line 1: IDVNM + document_last_9_digits + check_digit + 12_digits_document_number
            if line1.startswith('IDVNM'):
                mrz_data['document_type'] = 'ID'
                mrz_data['country_code'] = 'VNM'
                
                # Extract document_last_9_digits (positions 5-13)
                document_last_9_digits = line1[5:14]
                if document_last_9_digits.isdigit() and len(document_last_9_digits) == 9:
                    mrz_data['document_last_9_digits'] = document_last_9_digits
                    
                    # Extract check digit (position 14)
                    check_digit = line1[14]
                    if check_digit.isdigit():
                        mrz_data['check_digit'] = check_digit
                        
                        # Validate check digit for document_last_9_digits
                        calculated_check = self._calculate_mrz_check_digit(document_last_9_digits)
                        if calculated_check != check_digit:
                            logger.warning(f"MRZ check digit mismatch for document_last_9_digits: expected {calculated_check}, got {check_digit}")
                            mrz_data['check_digit_valid'] = False
                        else:
                            mrz_data['check_digit_valid'] = True
                    
                    # Extract 12_digits_document_number (positions 15-26)
                    document_number_12 = line1[15:27]
                    if document_number_12.isdigit() and len(document_number_12) == 12:
                        mrz_data['12_digits_document_number'] = document_number_12
                        mrz_data['mrz_document_number'] = document_number_12  # Legacy field
                    
                    # Extract optional field (positions 27-29)
                    optional_field = line1[27:30]
                    if optional_field and optional_field != '<<<':
                        mrz_data['optional'] = optional_field.replace('<', '')
            
            # Line 2: birth_date + check_digit + sex + expiry_date + check_digit + nationality + optional
            if len(line2) >= 30:
                try:
                    # Extract birth date (positions 0-5)
                    birth_date_str = line2[:6]
                    if birth_date_str.isdigit():
                        year = int(birth_date_str[:2])
                        month = int(birth_date_str[2:4])
                        day = int(birth_date_str[4:6])
                        # Assume years 00-30 are 2000-2030, 31-99 are 1931-1999
                        full_year = 2000 + year if year <= 30 else 1900 + year
                        mrz_data['birth_date'] = f"{day:02d}/{month:02d}/{full_year}"
                        mrz_data['mrz_dob'] = mrz_data['birth_date']  # Legacy field
                        
                        # Check digit for birth date (position 6)
                        birth_check_digit = line2[6]
                        if birth_check_digit.isdigit():
                            calculated_birth_check = self._calculate_mrz_check_digit(birth_date_str)
                            if calculated_birth_check != birth_check_digit:
                                logger.warning(f"MRZ check digit mismatch for birth_date: expected {calculated_birth_check}, got {birth_check_digit}")
                    
                    # Extract sex (position 7)
                    sex = line2[7]
                    if sex in ['M', 'F']:
                        mrz_data['sex'] = sex
                        mrz_data['mrz_sex'] = sex  # Legacy field
                    
                    # Extract expiry date (positions 8-13)
                    expiry_str = line2[8:14]
                    if expiry_str.isdigit():
                        year = int(expiry_str[:2])
                        month = int(expiry_str[2:4])
                        day = int(expiry_str[4:6])
                        full_year = 2000 + year if year <= 30 else 1900 + year
                        mrz_data['expiry'] = f"{day:02d}/{month:02d}/{full_year}"
                        mrz_data['mrz_expiry'] = mrz_data['expiry']  # Legacy field
                        
                        # Check digit for expiry date (position 14)
                        expiry_check_digit = line2[14]
                        if expiry_check_digit.isdigit():
                            calculated_expiry_check = self._calculate_mrz_check_digit(expiry_str)
                            if calculated_expiry_check != expiry_check_digit:
                                logger.warning(f"MRZ check digit mismatch for expiry: expected {calculated_expiry_check}, got {expiry_check_digit}")
                    
                    # Extract nationality (positions 15-17)
                    nationality = line2[15:18]
                    if nationality == 'VNM':
                        mrz_data['nationality'] = 'VNM'
                        mrz_data['mrz_nationality'] = 'VNM'  # Legacy field
                    
                    # Extract optional field (positions 18-29)
                    optional_field_2 = line2[18:30]
                    if optional_field_2 and optional_field_2 != '<<<<<<<<<<<<':
                        mrz_data['optional_2'] = optional_field_2.replace('<', '')
                            
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing line 2 of MRZ: {str(e)}")
            
            # Line 3: surname + given_names (30 characters total)
            if line3:
                # Parse name: SURNAME<<GIVEN_NAMES with < as filler
                name_clean = line3.replace('<', ' ').strip()
                name_parts = [part for part in name_clean.split() if part]
                
                if name_parts:
                    # First part is usually surname, rest are given names
                    surname = name_parts[0] if name_parts else ''
                    given_names = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                    
                    if surname:
                        mrz_data['surname'] = surname
                        mrz_data['mrz_surname'] = surname  # Legacy field
                    if given_names:
                        mrz_data['given_names'] = given_names
                        mrz_data['mrz_given_names'] = given_names  # Legacy field
                    
                    # Combine full name
                    full_name_parts = [given_names, surname] if given_names else [surname]
                    mrz_data['mrz_name'] = ' '.join(filter(None, full_name_parts))
        
        except Exception as e:
            logger.warning(f"Error parsing Vietnamese MRZ data: {str(e)}")
        
        return mrz_data
    
    def _parse_vietnamese_id_text(self, full_text: str, text_lines: list) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        Combines front and back parsing but prefers front-side extraction.
        """
        logger.warning("Using deprecated _parse_vietnamese_id_text method. Consider using _parse_vietnamese_id_front_text or _parse_vietnamese_id_back_text.")
        
        # Use front parsing as default
        result = self._parse_vietnamese_id_front_text(full_text, text_lines)
        
        # Try to add back-side fields if they exist
        back_result = self._parse_vietnamese_id_back_text(full_text, text_lines)
        result.update(back_result)
        
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
    
    def _extract_mrz(self, full_text: str, text_lines: list) -> Optional[Dict[str, Any]]:
        """Extract Machine Readable Zone (MRZ) from text lines using ICAO TD1 format
        
        Vietnamese ID MRZ format (TD1 - 30 characters per line):
        Line 1: IDVNM<document_last_9_digits><check_digit><12_digits_document_number>
        Line 2: <birth_date><check_digit><sex><expiry_date><check_digit><nationality><optional>
        Line 3: <surname><<GIVEN_NAMES<<<<<<<<<<<<<<<<<<<<<<<<<<
        """
        mrz_data = {}
        
        try:
            # Look for MRZ patterns in text lines with exact TD1 format
            mrz_patterns = [
                r'^IDVNM[0-9<]{25}$',      # Line 1: IDVNM + 25 chars (9 digits + 1 check + 12 digits + 3 optional)
                r'^[0-9]{6}[0-9][MF][0-9]{6}[0-9]VNM[<]*[0-9]?$',  # Line 2: YYMMDD + check + sex + YYMMDD + check + VNM + filler
                r'^[A-Z<]+$',              # Line 3: Name data with < fillers
            ]
            
            # Look for MRZ lines in the text
            for i, line in enumerate(text_lines):
                line_clean = line.strip().upper()
                
                # Ensure line is exactly 30 characters and matches MRZ pattern 1
                if len(line_clean) == 30 and re.match(mrz_patterns[0], line_clean):
                    mrz_data['mrz_line1'] = line_clean
                    
                    # Look for subsequent lines
                    if i + 1 < len(text_lines):
                        next_line = text_lines[i + 1].strip().upper()
                        if len(next_line) == 30 and re.match(mrz_patterns[1], next_line):
                            mrz_data['mrz_line2'] = next_line
                    
                    if i + 2 < len(text_lines):
                        third_line = text_lines[i + 2].strip().upper()
                        if len(third_line) == 30 and re.match(mrz_patterns[2], third_line):
                            mrz_data['mrz_line3'] = third_line
                    
                    break
            
            # Also try to find MRZ in the full text as continuous lines
            if not mrz_data:
                # Look for the pattern in continuous text (without spaces)
                full_text_clean = full_text.upper().replace(' ', '').replace('\n', '')
                
                # Try to find IDVNM pattern followed by potential MRZ data
                idvnm_match = re.search(r'IDVNM[0-9<]{25}', full_text_clean)
                if idvnm_match:
                    start_pos = idvnm_match.start()
                    
                    # Extract 3 lines of 30 characters each
                    if len(full_text_clean) >= start_pos + 90:  # 3 lines * 30 chars
                        potential_line1 = full_text_clean[start_pos:start_pos + 30]
                        potential_line2 = full_text_clean[start_pos + 30:start_pos + 60]
                        potential_line3 = full_text_clean[start_pos + 60:start_pos + 90]
                        
                        # Validate each line
                        if (re.match(mrz_patterns[0], potential_line1) and
                            re.match(mrz_patterns[1], potential_line2) and
                            re.match(mrz_patterns[2], potential_line3)):
                            
                            mrz_data['mrz_line1'] = potential_line1
                            mrz_data['mrz_line2'] = potential_line2
                            mrz_data['mrz_line3'] = potential_line3
            
            # If we found MRZ lines, parse them using our ICAO-compliant parser
            if 'mrz_line1' in mrz_data and 'mrz_line2' in mrz_data:
                parsed_mrz = self._parse_mrz_data(
                    mrz_data['mrz_line1'], 
                    mrz_data['mrz_line2'], 
                    mrz_data.get('mrz_line3', '')
                )
                mrz_data.update(parsed_mrz)
                return mrz_data
            
        except Exception as e:
            logger.warning(f"Error extracting MRZ: {str(e)}")
        
        return None if not mrz_data else mrz_data
    
    def _calculate_mrz_check_digit(self, data: str) -> str:
        """Calculate MRZ check digit using the 7,3,1 rule
        
        The check digit is calculated by:
        1. Assign values: 0-9 = face value, A-Z = 10-35, '<' (filler) = 0
        2. Multiply each value by weight (7,3,1,7,3,1,...)
        3. Sum all products
        4. Take modulo 10 of the sum
        
        Args:
            data: String to calculate check digit for
            
        Returns:
            Single digit check digit as string
        """
        def char_to_value(char: str) -> int:
            if char.isdigit():
                return int(char)
            elif char.isalpha():
                return ord(char.upper()) - ord('A') + 10
            else:  # '<' or other filler
                return 0
        
        weights = [7, 3, 1]
        total = 0
        
        for i, char in enumerate(data):
            weight = weights[i % 3]
            value = char_to_value(char)
            total += value * weight
        
        check_digit = total % 10
        return str(check_digit)
