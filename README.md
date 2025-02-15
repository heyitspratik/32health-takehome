# Project Setup

## Prerequisites
Ensure you have the following installed on your system:
- Docker
- Docker Compose

## Setup and Run the Project

### 1. Build the Docker Containers
To build the project from scratch, run the following command:
```bash
docker-compose build --no-cache
```
This ensures that all dependencies and configurations are freshly built.

### 2. Start the Containers
Once the build is complete, start the containers using:
```bash
docker-compose up -d
```
The `-d` flag runs the containers in detached mode (in the background).

### 3. Access the Application Container
To enter the running `claim_process` container and interact with it, use:
```bash
docker exec -it claim_process bash
```
This allows you to run commands inside the container, such as debugging or running tests.

## Running Tests
To run the test suite inside the container:
```bash
pytest tests/
```

## API Endpoints
You can test the API using `curl` or Postman. Example request to create a claim:
```bash
curl -X POST "http://localhost:8000/claims/" -H "Content-Type: application/json" -d '{
  "service_date": "2023-03-28",
  "submitted_procedure": "D0180",
  "plan_group": "GRP-1000",
  "subscriber": "3730189502",
  "provider_npi": "1497775530",
  "provider_fees": 100.00,
  "allowed_fees": 100.00,
  "member_coinsurance": 0.00,
  "member_copay": 0.00
}'
```

## Stopping and Cleaning Up
To stop and remove containers:
```bash
docker-compose down
```
This will stop the running containers and free up resources.

