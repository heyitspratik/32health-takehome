from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class PaymentRequest(BaseModel):
    provider_npi: str
    net_fee: float

@app.post("/process_payment")
def process_payment(payment: PaymentRequest):
    # Simulating payment processing
    if payment.net_fee <= 0:
        raise HTTPException(status_code=400, detail="Net fee must be greater than zero.")
    return {"message": f"Payment of {payment.net_fee} processed for provider {payment.provider_npi}"}
