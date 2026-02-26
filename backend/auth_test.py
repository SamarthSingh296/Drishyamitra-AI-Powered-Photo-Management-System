from app import create_app
from models.database import db
from models.user import User
import sys

app = create_app()

with app.app_context():
    print("--- Diagnostic Start ---")
    try:
        # Check if user exists
        test_user = User.query.filter_by(username='diag_user').first()
        if test_user:
            print("Cleaning up old test user...")
            db.session.delete(test_user)
            db.session.commit()

        print("Testing Registration...")
        new_user = User(username='diag_user', email='diag@example.com')
        new_user.set_password('password123')
        db.session.add(new_user)
        db.session.commit()
        print("Registration Success!")

        print("Testing Login...")
        login_user = User.query.filter_by(username='diag_user').first()
        if login_user and login_user.check_password('password123'):
            print("Login Success!")
        else:
            print("Login Failed: Credentials mismatch or user not found.")

    except Exception as e:
        print("\n--- ERROR DETECTED ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("--- Diagnostic End ---")
