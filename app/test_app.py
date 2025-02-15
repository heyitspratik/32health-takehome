import sys
import os

# Ensure /app is in the Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from main import app
import io
from fastapi import UploadFile

client = TestClient(app)

def test_create_claim():
    # Prepare request data
    data = {
        "service_date": "2023-03-28",
        "submitted_procedure": "D0180",
        "plan_group": "GRP-1000",
        "subscriber": "3730189502",
        "provider_npi": "1497775530",
        "provider_fees": 100,
        "allowed_fees": 100,
        "member_coinsurance": 0,
        "member_copay": 0
    }
    
    response = client.post("/claims/", json=data)
    
    assert response.status_code == 200
    assert response.json() == {"message": "Claim added and payment processed successfully"}



def test_get_claims():
    response = client.get("/claims/")
    
    assert response.status_code == 200
    # Check if the response contains the expected fields
    assert isinstance(response.json(), list)
    assert "submitted_procedure" in response.json()[0]
    assert "provider_fees" in response.json()[0]


def test_upload_csv():
    file_content = '''service_date,submitted_procedure,plan_group,subscriber,provider_npi,provider_fees,allowed_fees,member_coinsurance,member_copay
    2023-03-28,D0180,GRP-1000,3730189502,1497775530,100,100,0,0'''
    
    # Create an UploadFile object
    file = UploadFile(filename="claim_1234.csv", file=io.BytesIO(file_content.encode()))
    
    response = client.post("/upload_csv/", files={"file": file})
    
    assert response.status_code == 200
    assert response.json() == {"message": "Claims successfully processed"}
    
    
    
def test_get_top_providers():
    response = client.get("/top_providers/")
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert "provider_npi" in response.json()[0]
    assert "net_fees" in response.json()[0]

