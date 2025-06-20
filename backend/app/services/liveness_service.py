import cv2
import numpy as np
from typing import Dict, Any, List
import logging
# import dlib  # Removed - using OpenCV for face detection instead
from scipy.spatial import distance

logger = logging.getLogger(__name__)

class LivenessDetectionService:
    def __init__(self):
        # Use OpenCV cascade classifiers instead of dlib
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        logger.info("Liveness detection service initialized with OpenCV")
    
    def detect_liveness(self, image_path: str) -> Dict[str, Any]:
        """Comprehensive liveness detection"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                return {
                    'is_live': False,
                    'confidence': 0.0,
                    'error': 'Could not read image'
                }
            
            # Multiple liveness checks
            texture_score = self._texture_analysis(image)
            motion_score = self._motion_analysis(image)
            eye_blink_score = self._eye_blink_detection(image)
            face_depth_score = self._face_depth_analysis(image)
            reflection_score = self._reflection_analysis(image)
            
            # Combine scores
            scores = [texture_score, motion_score, eye_blink_score, face_depth_score, reflection_score]
            valid_scores = [s for s in scores if s >= 0]
            
            if not valid_scores:
                return {
                    'is_live': False,
                    'confidence': 0.0,
                    'error': 'No valid liveness metrics calculated'
                }
            
            overall_score = np.mean(valid_scores)
            is_live = overall_score > 0.6  # Threshold for liveness
            
            return {
                'is_live': is_live,
                'confidence': float(overall_score),
                'texture_score': float(texture_score) if texture_score >= 0 else None,
                'motion_score': float(motion_score) if motion_score >= 0 else None,
                'eye_blink_score': float(eye_blink_score) if eye_blink_score >= 0 else None,
                'face_depth_score': float(face_depth_score) if face_depth_score >= 0 else None,
                'reflection_score': float(reflection_score) if reflection_score >= 0 else None,
                'overall_score': float(overall_score)
            }
            
        except Exception as e:
            logger.error(f"Liveness detection failed: {str(e)}")
            return {
                'is_live': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _texture_analysis(self, image: np.ndarray) -> float:
        """Analyze image texture to detect photo vs real face"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate Local Binary Pattern (LBP) for texture analysis
            # Simplified version - in production use skimage.feature.local_binary_pattern
            
            # Calculate gradient magnitude
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Calculate texture variance
            texture_variance = np.var(gradient_magnitude)
            
            # Normalize score (higher variance indicates more texture/liveness)
            texture_score = min(1.0, texture_variance / 1000)
            
            return texture_score
            
        except Exception as e:
            logger.error(f"Texture analysis failed: {str(e)}")
            return -1
    
    def _motion_analysis(self, image: np.ndarray) -> float:
        """Analyze motion blur as indicator of liveness"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian variance (blur detection)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Some motion blur is good (indicates live capture)
            # But too much blur is bad
            if laplacian_var < 50:
                return 0.2  # Too blurry
            elif laplacian_var > 500:
                return 0.9  # Good sharpness
            else:
                # Moderate blur - could indicate liveness
                return 0.6
                
        except Exception as e:
            logger.error(f"Motion analysis failed: {str(e)}")
            return -1
    
    def _eye_blink_detection(self, image: np.ndarray) -> float:
        """Detect eye patterns using OpenCV"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces using OpenCV
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return -1
            
            # Get the largest face
            (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
            face_roi = gray[y:y+h, x:x+w]
            
            # Detect eyes in the face region
            eyes = self.eye_cascade.detectMultiScale(face_roi, 1.1, 3)
            
            # Score based on eye detection
            if len(eyes) >= 2:
                # Two eyes detected - good sign for liveness
                return 0.8
            elif len(eyes) == 1:
                # One eye detected - moderate score
                return 0.5
            else:
                # No eyes detected - low score
                return 0.2
                
        except Exception as e:
            logger.error(f"Eye detection failed: {str(e)}")
            return -1
    
    def _face_depth_analysis(self, image: np.ndarray) -> float:
        """Analyze face depth/3D characteristics"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate image gradients to detect 3D structure
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient direction variance
            gradient_angles = np.arctan2(grad_y, grad_x)
            angle_variance = np.var(gradient_angles)
            
            # Higher variance indicates more 3D structure
            depth_score = min(1.0, angle_variance / 2)
            
            return depth_score
            
        except Exception as e:
            logger.error(f"Face depth analysis failed: {str(e)}")
            return -1
    
    def _reflection_analysis(self, image: np.ndarray) -> float:
        """Analyze reflections and lighting patterns"""
        try:
            # Convert to HSV for better light analysis
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]  # Value channel
            
            # Detect bright spots (potential screen reflections)
            bright_spots = np.sum(v_channel > 240)
            total_pixels = v_channel.size
            bright_ratio = bright_spots / total_pixels
            
            # Too many bright spots might indicate screen reflection
            if bright_ratio > 0.1:
                return 0.3  # Likely screen reflection
            elif bright_ratio > 0.05:
                return 0.6  # Some reflections (normal)
            else:
                return 0.8  # Good lighting
                
        except Exception as e:
            logger.error(f"Reflection analysis failed: {str(e)}")
            return -1
    
    def detect_screen_patterns(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect screen patterns that indicate photo of photo"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply FFT to detect regular patterns
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.log(np.abs(f_shift) + 1)
            
            # Look for regular patterns in frequency domain
            # Screen patterns would show up as regular frequencies
            
            # Calculate variance in frequency domain
            freq_variance = np.var(magnitude_spectrum)
            
            # High variance might indicate screen patterns
            screen_pattern_detected = freq_variance > 10
            
            return {
                'screen_pattern_detected': screen_pattern_detected,
                'frequency_variance': float(freq_variance),
                'confidence': min(1.0, freq_variance / 20)
            }
            
        except Exception as e:
            logger.error(f"Screen pattern detection failed: {str(e)}")
            return {
                'screen_pattern_detected': False,
                'error': str(e),
                'confidence': 0
            }
