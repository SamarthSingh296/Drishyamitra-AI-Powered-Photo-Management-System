import os
from flask import Flask
from models.database import db
from services.face_recognition import FaceRecognitionService
from config import Config
import logging

logging.basicConfig(level=logging.INFO)

# Dummy app to initialize config and context
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def test_pipeline():
    print("=== Testing Face Recognition Pipeline ===")
    with app.app_context():
        service = FaceRecognitionService()
        
        # We need a sample image to test with.
        # Use the data/photos folder provided by the user
        test_dir = 'data/photos'
        os.makedirs(test_dir, exist_ok=True)
        
        images = [f for f in os.listdir(test_dir) if f.endswith(('jpg', 'jpeg', 'png'))]
        
        if not images:
            print(f"No test images found in {test_dir}.")
            print(f"Please drop a .jpg or .png file inside 'backend/{test_dir}' and run this script again.")
            return
            
        print(f"Found {len(images)} test image(s) in {test_dir}\n")
        
        for image_name in images:
            test_image_path = os.path.join(test_dir, image_name)
            print(f"--- Processing: {image_name} ---")
            
            print(f"Detecting and extracting faces using {service.model_name} and {service.detector_backend}...")
            faces = service.detect_and_extract_faces(test_image_path)
            
            if faces:
                print(f"SUCCESS! Detected {len(faces)} face(s) in {image_name}.")
                for i, face in enumerate(faces):
                    conf = face.get('face_confidence', 'N/A')
                    print(f"  Face {i+1}: Confidence {conf}")
            else:
                print(f"WARNING: No faces detected or an error occurred for {image_name}.")
            print("-" * 40 + "\n")

if __name__ == "__main__":
    test_pipeline()
