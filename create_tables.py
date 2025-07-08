from database import engine, Base
from models import pdf_file, extracted_data

def create_tables():
    print("Creating tables in the database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    create_tables()
