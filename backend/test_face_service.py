import os
from app import create_app
from services.face_recognition import FaceRecognitionService
from deepface import DeepFace

def verify_face_service():
    app = create_app()
    with app.app_context():
        service = FaceRecognitionService()
        
        # We need a sample image to test with
        test_img_path = os.path.join(app.config['UPLOAD_FOLDER'], 'test_photo.jpg')
        
        # If test image doesn't exist, we can't fully run it, but we can verify imports
        if not os.path.exists(test_img_path):
            print(f"Skipping actual extraction: Please place a dummy image at {test_img_path} to test")
            print("Imports and service initialization succeeded.")
            return

        print(f"Testing extraction on {test_img_path}...")
        results = service.detect_and_extract_faces(test_img_path)
        
        print(f"Found {len(results)} faces.")
        for i, face in enumerate(results):
            emb = face.get("embedding", [])
            print(f"Face {i+1}: Embedding Size = {len(emb)}")

if __name__ == "__main__":
    verify_face_service()
