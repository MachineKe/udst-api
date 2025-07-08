from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class PDFFile(Base):
    __tablename__ = "pdf_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    metadata = Column(String(1024), nullable=True)

    extracted_data = relationship("ExtractedData", back_populates="pdf_file")
