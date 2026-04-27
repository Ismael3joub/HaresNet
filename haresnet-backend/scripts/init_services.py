import sys
import os
sys.path.append(os.getcwd())

from app import create_app, db
from app.services.service_manager import ServiceManager

app = create_app()
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Tables created.")
    
    print("Initializing services...")
    sm = ServiceManager()
    sm.initialize_services()
    print("Done.")
