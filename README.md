# EchoFi KYC Microservice

A minimal-cost, open-source KYC (Know Your Customer) microservice that provides document verification, face matching, and sanctions checking capabilities.

## Features

- Document OCR (English, Vietnamese, Chinese Simplified)
- Face matching and basic liveness detection
- Sanctions list checking
- Encrypted storage of sensitive data
- REST API interface
- Containerized deployment

## Architecture

The service able to run on a single EC2 instance with the following components:
- FastAPI backend
- RabbitMQ for job queuing
- PostgreSQL for data storage
- MinIO/S3 for document storage
- Multiple worker services for OCR, face matching, and sanctions checking

## Performance Targets

- Throughput: 1,000 verifications/day (≈1 req/90s)
- Burst capacity: 5 req/min
- Latency: P95 ≤ 4s per verification
- Cost: ≤ $120/month on AWS

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your environment variables
3. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

## API Documentation

The API documentation is available at `/docs` when running the service.

### Main Endpoints

- `POST /kyc/submit` - Submit KYC verification
- `GET /kyc/status/{ticket}` - Check verification status
- `GET /admin/pending` - List pending verifications
- `POST /admin/review/{ticket}` - Review verification

## Development

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15
- RabbitMQ

### Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Deployment

The service can be deployed using Terraform:

```bash
cd terraform
terraform init
terraform apply
```

## License

MIT License 