from app import create_app
import sys

try:
    print("Testing Application Creation...")
    app = create_app()
    print("Success: Application factory initialized.")
    
    print("\nTesting Database Connection...")
    with app.app_context():
        from models.database import db
        # try a simple query
        db.session.execute('SELECT 1')
        print("Success: Database is reachable.")
        
except Exception as e:
    print(f"\nCRITICAL ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
