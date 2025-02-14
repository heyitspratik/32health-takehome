from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

class ClaimCreate(BaseModel):
    service_date: str
    submitted_procedure: str
    plan_group: str
    subscriber: str
    provider_npi: str
    provider_fees: Decimal  
    allowed_fees: Decimal   
    member_coinsurance: Decimal  
    member_copay: Decimal   

    class Config:
        orm_mode = True

class TopProvider(BaseModel):
    provider_npi: str
    total_net_fee: Decimal
