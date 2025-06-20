from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.user import User
from app.models.kyc_job import KYCJob

def init_db(db: Session) -> None:
    # Create all tables
    Base.metadata.create_all(bind=db.get_bind()) 