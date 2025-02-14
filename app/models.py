from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal

class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_date: str
    submitted_procedure: str
    plan_group: str
    subscriber: str
    provider_npi: str
    provider_fees: Decimal
    allowed_fees: Decimal
    member_coinsurance: Decimal
    member_copay: Decimal
    net_fee: Decimal = Field(default=0)
    quadrant: Optional[str] = None

    def compute_net_fee(self):
        self.net_fee = self.provider_fees + self.member_coinsurance + self.member_copay - self.allowed_fees
