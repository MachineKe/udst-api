from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id = Column(Integer, primary_key=True, index=True)
    pdf_file_id = Column(Integer, ForeignKey("pdf_files.id"), nullable=False)
    key = Column(String(255), nullable=False)  # e.g., field name or label
    value = Column(String(255), nullable=True)  # extracted value as string
    extracted_date = Column(DateTime, default=datetime.utcnow)
    month = Column(String(7), nullable=True)  # e.g., "2025-07"

    pdf_file = relationship("PDFFile", back_populates="extracted_data")
