import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import Base
from app.models.user import User  # Import User model first
from app.models.kyc_job import KYCJob
from app.models.audit_log import AuditLog

# Use the database URL from the environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://kyc_user:kyc_password@localhost:5432/kyc_db')

# Create the database engine
engine = create_engine(DATABASE_URL)

# Create the tables
Base.metadata.create_all(engine) 