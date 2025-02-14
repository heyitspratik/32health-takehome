from fastapi import FastAPI, UploadFile, Depends, File, HTTPException
from sqlmodel import Session, SQLModel, Field
from typing import List, Optional
from decimal import Decimal
import csv
from io import StringIO
from db import get_session, create_db_and_tables
from models import Claim
from collections import defaultdict
import redis
from redis.exceptions import LockError
import time
import pandas as pd
import requests
import io
import re
import logging

app = FastAPI()

PAYMENTS_SERVICE_URL = "http://payments:8001/process_payment"

r = redis.StrictRedis(host='redis', port=6379, db=0)

def acquire_lock(lock_name: str, timeout: int = 30):
    lock = r.lock(lock_name, timeout=timeout)
    if lock.acquire(blocking=False):
        return lock
    return None

def release_lock(lock):
    if lock:
        lock.release()

def send_payment_request(provider_npi: str, net_fee: float):
    if net_fee > 0:
        payload = {"provider_npi": str(provider_npi), "net_fee": net_fee}
        try:
            response = requests.post(PAYMENTS_SERVICE_URL, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending payment request: {e}")


# Validation function for a single claim
def validate_claim_data(claim_data):
    if not claim_data['submitted_procedure'].startswith("D"):
        raise HTTPException(
            status_code=400,
            detail="Invalid 'submitted_procedure'. It should begin with 'D'."
        )

    if not re.match(r'^\d{10}$', str(claim_data['provider_npi'])):
        raise HTTPException(
            status_code=400,
            detail="Invalid 'Provider NPI'. It should be a 10-digit number."
        )

    required_fields = ["submitted_procedure", "provider_npi", "allowed_fees", "provider_fees", 
                       "member_coinsurance", "member_copay", "service_date", "plan_group", "subscriber"]
    for field in required_fields:
        if field not in claim_data:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required field: {field}"
            )

# Create database tables at startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "Healthy"}

# Endpoint to get all claims
@app.get("/claims/", response_model=List[Claim])
def get_all_claims(db: Session = Depends(get_session)):
    try:
        claims = db.query(Claim).all()
        return claims
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching claims: {str(e)}")

# Endpoint to create a new claim
@app.post("/claims/")
def create_claim(claim: Claim, db: Session = Depends(get_session)):
    db.begin()
    try:
        validate_claim_data(claim.dict())
        claim.member_coinsurance = parse_fee(claim.member_coinsurance)
        claim.member_copay = parse_fee(claim.member_copay)
        claim.provider_fees = parse_fee(claim.provider_fees)
        claim.allowed_fees = parse_fee(claim.allowed_fees)
        db.add(claim)
        db.commit()
        db.refresh(claim)

        lock = acquire_lock(f"payment-{claim.provider_npi}")
        if lock:
            try:
                if claim.net_fee > 0:
                    send_payment_request(claim.provider_npi, claim.net_fee)
            except Exception as payment_error:
                db.rollback() 
                release_lock(lock)
                raise HTTPException(status_code=500, detail="Payment processing failed")
            release_lock(lock)
        else:
            raise HTTPException(status_code=400, detail="Payment service is temporarily busy")

        return {"message": "Claim added and payment processed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding claim: {str(e)}")

# Function to convert string values like "$100.00" to float
def parse_fee(value) -> float:
    try:
        if isinstance(value, (int, float)):
            return float(value)

        if not value or value.strip() == '':
            return 0.0

        return float(value.replace('$', '').replace(',', ''))
    except ValueError:
        return 0.0

# Endpoint to process csv and create a new claims out of it
@app.post("/upload_csv/")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_session)):
    db.begin()
    try:
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))

        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

        for _, row in df.iterrows():
            
            validate_claim_data(row.to_dict())
            quadrant = row["quadrant"] if isinstance(row["quadrant"], str) else None
            provider_fees = parse_fee(row["provider_fees"])
            allowed_fees = parse_fee(row["allowed_fees"])
            member_coinsurance = parse_fee(row["member_coinsurance"])
            member_copay = parse_fee(row["member_copay"])

            net_fee = provider_fees + member_coinsurance + member_copay - allowed_fees
            
            claim = Claim(
                service_date=row["service_date"],
                submitted_procedure=row["submitted_procedure"],
                quadrant=quadrant,
                plan_group=row["plan_group"],
                subscriber=row["subscriber"],
                provider_npi=row["provider_npi"],
                provider_fees=parse_fee(row["provider_fees"]),
                allowed_fees=parse_fee(row["allowed_fees"]),
                member_coinsurance=parse_fee(row["member_coinsurance"]),
                member_copay=parse_fee(row["member_copay"]),
                net_fee=(parse_fee(row["provider_fees"]) + parse_fee(row["member_coinsurance"]) +
                         parse_fee(row["member_copay"]) - parse_fee(row["allowed_fees"])),
            )
            db.add(claim)

            # Handle payment request communication with the payments service
            # If claim has a valid net_fee, send the payment request
            # Acquire lock to prevent multiple services from processing payment concurrently
            lock = acquire_lock(f"payment-{claim.provider_npi}")
            if lock:
                try:
                    if claim.net_fee > 0:
                        # Send the payment request to payments service
                        send_payment_request(claim.provider_npi, net_fee)
                except Exception as payment_error:
                    # If payment fails, roll back the claim and raise an error
                    db.rollback() # Rollback transaction for this claim
                    release_lock(lock) # Release the lock
                    raise HTTPException(status_code=500, detail="Payment processing failed")
                release_lock(lock)  # Release the lock after successful payment processing
            else:
                # If lock is not acquired, it means another instance is processing this claim
                raise HTTPException(status_code=400, detail=f"Payment service is temporarily busy for provider {claim.provider_npi}")

        db.commit() # Commit the claims if everything is processed successfully
        return {"message": "Claims successfully processed"}

    except Exception as e:
        # If any error occurs in the CSV processing or payment request, rollback the transaction
        db.rollback()  # Rollback the entire transaction in case of failure
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")


# Endpoint to get top 10 providers by net fees
@app.get("/top_providers/")
def get_top_providers(db: Session = Depends(get_session)):
    try:
        claims = db.query(Claim).all()
        provider_net_fees = defaultdict(float)

        for claim in claims:
            provider_net_fees[claim.provider_npi] += float(claim.net_fee)

        top_providers = sorted(provider_net_fees.items(), key=lambda x: x[1], reverse=True)[:10]

        result = [{"provider_npi": provider[0], "net_fees": provider[1]} for provider in top_providers]

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top providers: {str(e)}")

