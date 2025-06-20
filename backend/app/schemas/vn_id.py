from pydantic import BaseModel
from typing import Optional

class VietnameseIDCard(BaseModel):
    id_number: str
    full_name: str
    dob: str
    gender: Optional[str]
    nationality: Optional[str]
    address: Optional[str]
    issue_date: Optional[str]
    expiry_date: Optional[str]
    place_of_issue: Optional[str]
    other_fields: Optional[dict] = None 