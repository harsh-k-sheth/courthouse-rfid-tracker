# Deployment Guide

## Prerequisites

- AWS Account with IAM permissions for IoT Core, Lambda, DynamoDB, API Gateway, CloudWatch
- AWS CLI configured (`aws configure`)
- Terraform 1.5+
- Python 3.11+
- Docker (for local development)
- A Raspberry Pi or Linux box for the edge gateway (for production)

## Local Development

### 1. Start Infrastructure

```bash
cd infrastructure/docker
docker-compose up -d
```

This starts DynamoDB Local (port 8000) and Mosquitto MQTT broker (port 1883).

### 2. Seed Test Data

```bash
export DYNAMODB_ENDPOINT=http://localhost:8000
export AWS_ACCESS_KEY_ID=local
export AWS_SECRET_ACCESS_KEY=local
export AWS_DEFAULT_REGION=us-east-1

python scripts/seed_readers.py
python scripts/seed_files.py
```

### 3. Run the Simulator

```bash
# Stationary files at random locations
python scripts/simulate_readers.py --mode stationary --duration 60

# File movement between rooms
python scripts/simulate_readers.py --mode movement

# Overlap zone testing
python scripts/simulate_readers.py --mode overlap
```

### 4. Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ -v --cov=src --cov-report=html
```

## AWS Deployment

### 1. Package Lambda Functions

```bash
# Create deployment package
mkdir -p build
pip install -r requirements.txt -t build/
cp -r src/ build/
cd build && zip -r ../infrastructure/terraform/environments/dev/lambda_package.zip . && cd ..
rm -rf build
```

### 2. Deploy Infrastructure

```bash
cd infrastructure/terraform/environments/dev

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var="stage=dev"

# Deploy
terraform apply -var="stage=dev"
```

Terraform will output the API endpoint URL and IoT Core endpoint.

### 3. Register IoT Thing (Gateway)

```bash
# Create IoT thing for the gateway
aws iot create-thing --thing-name courthouse-gateway-floor1

# Create certificates
aws iot create-keys-and-certificate \
  --set-as-active \
  --certificate-pem-outfile gateway.cert.pem \
  --public-key-outfile gateway.public.key \
  --private-key-outfile gateway.private.key

# Attach policy (create policy first, see IoT Core console)
aws iot attach-policy \
  --policy-name courthouse-rfid-gateway-policy \
  --target <certificate-arn>

# Attach certificate to thing
aws iot attach-thing-principal \
  --thing-name courthouse-gateway-floor1 \
  --principal <certificate-arn>
```

### 4. Configure Gateway

Copy certificates to the gateway device and update `config.yaml`:

```bash
scp gateway.cert.pem gateway.private.key pi@gateway-ip:/etc/rfid-gateway/certs/
```

Update `src/gateway/config.yaml` with:
- Your IoT Core endpoint (from `terraform output`)
- Certificate file paths
- Reader IP addresses for your physical installation

### 5. Start Gateway

```bash
# On the Raspberry Pi
cd /opt/rfid-gateway
python gateway.py --config config.yaml
```

### 6. Deploy Dashboard

```bash
cd src/dashboard
npm install
npm run build

# Upload to S3 + CloudFront, or deploy to Vercel/Netlify
# Update API_URL in the dashboard config to point to the API Gateway endpoint
```

## Production Considerations

### Scaling to Multiple Courthouses

Each courthouse gets its own gateway(s). All gateways point to the same IoT Core endpoint. The cloud backend scales automatically through Lambda and DynamoDB on-demand capacity.

### Monitoring

CloudWatch alarms are deployed by Terraform for Lambda errors. Additional recommended alarms:
- DynamoDB throttling events
- IoT Core message delivery failures
- Gateway heartbeat gaps (reader offline detection)

### Security

- IoT connections use mutual TLS (X.509 certificates per gateway)
- API Gateway should be configured with Cognito or API key authentication
- DynamoDB tables should have point-in-time recovery enabled for production
- Enable VPC endpoints if Lambda functions need to stay within a VPC

### Backup

- DynamoDB: Enable point-in-time recovery and on-demand backups
- Movement history: TTL automatically expires records after 90 days
- Reader and tag registries: Export periodically to S3
