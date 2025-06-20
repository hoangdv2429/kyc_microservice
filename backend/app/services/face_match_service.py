import cv2
import numpy as np
from typing import Dict, Any, Tuple
import logging
from deepface import DeepFace
import os

logger = logging.getLogger(__name__)

class FaceMatchingService:
    def __init__(self):
        self.model_name = "VGG-Face"  # Can be changed to other models like Facenet, OpenFace
        self.distance_metric = "cosine"
        self.detection_backend = "opencv"
        
    def compare_faces(self, id_image_path: str, selfie_image_path: str) -> Dict[str, Any]:
        """Compare face in ID card with selfie"""
        try:
            # Verify both images exist
            if not os.path.exists(id_image_path) or not os.path.exists(selfie_image_path):
                raise ValueError("One or both image files not found")
            
            # Extract face from ID card
            id_face = self._extract_face_from_id(id_image_path)
            if id_face is None:
                return {
                    'match': False,
                    'confidence': 0.0,
                    'error': 'No face detected in ID card',
                    'distance': 1.0
                }
            
            # Extract face from selfie
            selfie_face = self._extract_face_from_selfie(selfie_image_path)
            if selfie_face is None:
                return {
                    'match': False,
                    'confidence': 0.0,
                    'error': 'No face detected in selfie',
                    'distance': 1.0
                }
            
            # Use DeepFace to compare faces
            result = DeepFace.verify(
                img1_path=id_image_path,
                img2_path=selfie_image_path,
                model_name=self.model_name,
                distance_metric=self.distance_metric,
                detector_backend=self.detection_backend
            )
            
            # Calculate confidence score (inverse of distance)
            distance = result['distance']
            threshold = result['threshold']
            confidence = max(0, 1 - (distance / threshold))
            
            return {
                'match': result['verified'],
                'confidence': float(confidence),
                'distance': float(distance),
                'threshold': float(threshold),
                'model_used': self.model_name,
                'face_detected_id': True,
                'face_detected_selfie': True
            }
            
        except Exception as e:
            logger.error(f"Face matching failed: {str(e)}")
            return {
                'match': False,
                'confidence': 0.0,
                'error': str(e),
                'distance': 1.0
            }
    
    def _extract_face_from_id(self, id_image_path: str) -> np.ndarray:
        """Extract face region from ID card image"""
        try:
            image = cv2.imread(id_image_path)
            if image is None:
                return None
            
            # Convert to RGB for face detection
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Use OpenCV face detector
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None
            
            # Take the largest face detected
            largest_face = max(faces, key=lambda x: x[2] * x[3])
            x, y, w, h = largest_face
            
            # Extract face region with some padding
            padding = int(0.2 * min(w, h))
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(image.shape[1], x + w + padding)
            y2 = min(image.shape[0], y + h + padding)
            
            face_region = image[y1:y2, x1:x2]
            return face_region
            
        except Exception as e:
            logger.error(f"Face extraction from ID failed: {str(e)}")
            return None
    
    def _extract_face_from_selfie(self, selfie_image_path: str) -> np.ndarray:
        """Extract face region from selfie image"""
        try:
            image = cv2.imread(selfie_image_path)
            if image is None:
                return None
            
            # Use OpenCV face detector
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None
            
            # Take the largest face detected
            largest_face = max(faces, key=lambda x: x[2] * x[3])
            x, y, w, h = largest_face
            
            face_region = image[y:y+h, x:x+w]
            return face_region
            
        except Exception as e:
            logger.error(f"Face extraction from selfie failed: {str(e)}")
            return None
    
    def detect_multiple_faces(self, image_path: str) -> Dict[str, Any]:
        """Detect if image contains multiple faces (security check)"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {'faces_count': 0, 'multiple_faces': False}
            
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            return {
                'faces_count': len(faces),
                'multiple_faces': len(faces) > 1,
                'face_detected': len(faces) > 0
            }
            
        except Exception as e:
            logger.error(f"Multiple face detection failed: {str(e)}")
            return {'faces_count': 0, 'multiple_faces': False, 'error': str(e)}
    
    def calculate_face_quality_score(self, image_path: str) -> Dict[str, Any]:
        """Calculate face quality metrics"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {'quality_score': 0, 'error': 'Could not read image'}
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate sharpness (Laplacian variance)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Calculate brightness
            brightness = np.mean(gray)
            
            # Calculate contrast
            contrast = gray.std()
            
            # Detect face
            face_detection = self.detect_multiple_faces(image_path)
            
            # Overall quality score (0-1)
            quality_score = min(1.0, (sharpness / 500 + 
                                    min(brightness / 128, 1.0) + 
                                    contrast / 64) / 3)
            
            return {
                'quality_score': float(quality_score),
                'sharpness': float(sharpness),
                'brightness': float(brightness),
                'contrast': float(contrast),
                'face_detected': face_detection['face_detected'],
                'multiple_faces': face_detection['multiple_faces']
            }
            
        except Exception as e:
            logger.error(f"Face quality calculation failed: {str(e)}")
            return {'quality_score': 0, 'error': str(e)}
