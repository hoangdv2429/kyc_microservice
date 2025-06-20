import cv2
import numpy as np
from pathlib import Path
import random

def create_id_card(text, output_path):
    """Create a mock ID card with text."""
    # Create a white background
    img = np.ones((800, 1200, 3), dtype=np.uint8) * 255
    
    # Add some random patterns
    for _ in range(100):
        x = random.randint(0, 1199)
        y = random.randint(0, 799)
        cv2.circle(img, (x, y), 1, (200, 200, 200), -1)
    
    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    y = 100
    for line in text.split('\n'):
        cv2.putText(img, line, (50, y), font, 1, (0, 0, 0), 2)
        y += 50
    
    # Add a border
    cv2.rectangle(img, (0, 0), (1199, 799), (0, 0, 0), 2)
    
    # Save the image
    cv2.imwrite(str(output_path), img)

def create_selfie(output_path):
    """Create a mock selfie image."""
    # Create a gradient background
    img = np.zeros((800, 600, 3), dtype=np.uint8)
    for i in range(800):
        color = int(255 * (1 - i/800))
        img[i, :] = [color, color, color]
    
    # Add a simple face shape
    center = (300, 400)
    cv2.ellipse(img, center, (150, 200), 0, 0, 360, (255, 220, 180), -1)
    
    # Add eyes
    cv2.circle(img, (center[0]-50, center[1]-50), 20, (0, 0, 0), -1)
    cv2.circle(img, (center[0]+50, center[1]-50), 20, (0, 0, 0), -1)
    
    # Add mouth
    cv2.ellipse(img, (center[0], center[1]+50), (50, 20), 0, 0, 180, (0, 0, 0), 2)
    
    # Save the image
    cv2.imwrite(str(output_path), img)

def main():
    # Create test data directory
    test_dir = Path("test_data")
    test_dir.mkdir(exist_ok=True)
    
    # Create ID card front
    id_text = """ID CARD
Name: John Doe
DOB: 1990-01-01
ID: 123456789
Address: 123 Main St
City: New York
Country: USA"""
    create_id_card(id_text, test_dir / "id_front.jpg")
    
    # Create ID card back
    back_text = """ID CARD BACK
Issued: 2020-01-01
Expires: 2030-01-01
Authority: DMV
Additional Info: None"""
    create_id_card(back_text, test_dir / "id_back.jpg")
    
    # Create selfie
    create_selfie(test_dir / "selfie.jpg")
    
    print("Test data generated successfully!")
    print(f"Files created in {test_dir}:")
    for file in test_dir.glob("*.jpg"):
        print(f"- {file.name}")

if __name__ == "__main__":
    main() 