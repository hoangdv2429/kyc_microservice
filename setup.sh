#!/bin/bash

# KYC Microservice Setup and Deployment Script
# This script sets up the complete KYC system with all required services

set -e

echo "🚀 Setting up KYC Microservice System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_section "Checking Dependencies"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed"
}

# Create required directories
create_directories() {
    print_section "Creating Required Directories"
    
    mkdir -p models
    mkdir -p nginx/ssl
    mkdir -p grafana/dashboards
    mkdir -p grafana/datasources
    mkdir -p logs
    
    print_status "Directories created"
}

# Create environment file if it doesn't exist
create_env_file() {
    print_section "Setting up Environment Configuration"
    
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cat > .env << EOF
# Database Configuration
POSTGRES_SERVER=postgres
POSTGRES_USER=kyc_user
POSTGRES_PASSWORD=kyc_secure_password_$(openssl rand -hex 8)
POSTGRES_DB=kyc_db

# RabbitMQ Configuration
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=kyc_user
RABBITMQ_PASSWORD=kyc_secure_password_$(openssl rand -hex 8)

# MinIO Configuration
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=kyc_minio_user
MINIO_SECRET_KEY=kyc_minio_password_$(openssl rand -hex 16)
MINIO_BUCKET=kyc-documents
MINIO_SECURE=false

# Security Configuration
SECRET_KEY=$(openssl rand -hex 32)
AES_ENCRYPTION_KEY=$(openssl rand -hex 32)

# Email Configuration (Update with your SMTP settings)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
FROM_EMAIL=noreply@echofi.com

# Telegram Configuration (Update with your bot token)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_ADMIN_CHAT_ID=your-admin-chat-id

# KYC Configuration
AUTO_APPROVAL_THRESHOLD=0.85
MANUAL_REVIEW_THRESHOLD=0.65
KYC_DATA_RETENTION_DAYS=1825
AUDIT_LOG_RETENTION_DAYS=2555

# Smart Contract Configuration
BLOCKCHAIN_RPC_URL=https://mainnet.infura.io/v3/your-project-id
CONTRACT_ADDRESS=0x1234567890123456789012345678901234567890
CONTRACT_PRIVATE_KEY=your-private-key

# Monitoring Configuration
GRAFANA_PASSWORD=admin_$(openssl rand -hex 8)

# Performance Settings
MAX_REQUESTS_PER_DAY=1000
OCR_TIMEOUT_SECONDS=30
FACE_MATCH_TIMEOUT_SECONDS=15

# Compliance Settings
GDPR_AUTO_DELETE_ENABLED=true
EOF
        print_status ".env file created with secure random passwords"
        print_warning "Please update the email, telegram, and blockchain configuration in .env file"
    else
        print_status ".env file already exists"
    fi
}

# Download AI models
download_models() {
    print_section "Downloading AI Models"
    
    if [ ! -f models/shape_predictor_68_face_landmarks.dat ]; then
        print_status "Downloading face landmark predictor model..."
        curl -L -o models/shape_predictor_68_face_landmarks.dat.bz2 \
            "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
        cd models && bunzip2 shape_predictor_68_face_landmarks.dat.bz2 && cd ..
        print_status "Face landmark model downloaded"
    else
        print_status "Face landmark model already exists"
    fi
}

# Create nginx configuration
create_nginx_config() {
    print_section "Creating Nginx Configuration"
    
    if [ ! -f nginx/nginx.conf ]; then
        cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:8080;
    }

    server {
        listen 80;
        server_name localhost;

        # Redirect HTTP to HTTPS in production
        # return 301 https://\$server_name\$request_uri;

        location / {
            proxy_pass http://api_backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            
            # Handle large file uploads for document submission
            client_max_body_size 50M;
            proxy_read_timeout 300s;
            proxy_connect_timeout 300s;
        }

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # HTTPS configuration (uncomment for production)
    # server {
    #     listen 443 ssl http2;
    #     server_name localhost;
    #     
    #     ssl_certificate /etc/nginx/ssl/cert.pem;
    #     ssl_certificate_key /etc/nginx/ssl/key.pem;
    #     
    #     location / {
    #         proxy_pass http://api_backend;
    #         proxy_set_header Host \$host;
    #         proxy_set_header X-Real-IP \$remote_addr;
    #         proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    #         proxy_set_header X-Forwarded-Proto https;
    #     }
    # }
}
EOF
        print_status "Nginx configuration created"
    fi
}

# Create Grafana dashboards
create_grafana_dashboards() {
    print_section "Setting up Grafana Dashboards"
    
    # Create datasource configuration
    cat > grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    # Create dashboard provisioning
    cat > grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'KYC Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    print_status "Grafana configuration created"
}

# Build and start services
start_services() {
    print_section "Building and Starting Services"
    
    print_status "Building Docker images..."
    docker-compose build --no-cache
    
    print_status "Starting infrastructure services..."
    docker-compose up -d postgres redis rabbitmq minio elasticsearch
    
    print_status "Waiting for infrastructure to be ready..."
    sleep 30
    
    print_status "Starting application services..."
    docker-compose up -d api worker-kyc worker-notifications worker-blockchain celery-beat
    
    print_status "Starting monitoring services..."
    docker-compose up -d prometheus grafana kibana celery-flower nginx
    
    print_status "All services started!"
}

# Run database migrations
run_migrations() {
    print_section "Running Database Migrations"
    
    print_status "Waiting for database to be ready..."
    sleep 10
    
    print_status "Running migrations..."
    docker-compose exec api python -m alembic upgrade head
    
    print_status "Database migrations completed"
}

# Setup MinIO buckets
setup_storage() {
    print_section "Setting up Object Storage"
    
    print_status "Setting up MinIO buckets..."
    docker-compose up -d minio-setup
    
    print_status "Storage setup completed"
}

# Display service URLs
show_service_urls() {
    print_section "Service URLs"
    
    echo -e "${GREEN}✅ Setup completed successfully!${NC}\n"
    
    echo "Service URLs:"
    echo "📁 KYC API: http://localhost"
    echo "📊 Grafana Dashboard: http://localhost:3000 (admin/admin)"
    echo "🔍 Prometheus: http://localhost:9090"
    echo "📋 RabbitMQ Management: http://localhost:15672"
    echo "💾 MinIO Console: http://localhost:9001"
    echo "🌸 Celery Flower: http://localhost:5555"
    echo "📈 Kibana: http://localhost:5601"
    echo ""
    echo "API Documentation: http://localhost/docs"
    echo "Admin Panel: http://localhost/api/v1/admin/dashboard"
    
    print_warning "Please update your .env file with proper email, telegram, and blockchain configurations"
    print_warning "For production, enable HTTPS in nginx configuration and use proper SSL certificates"
}

# Health check
health_check() {
    print_section "Running Health Check"
    
    sleep 20
    
    # Check API health
    if curl -f http://localhost/health > /dev/null 2>&1; then
        print_status "✅ API is healthy"
    else
        print_error "❌ API health check failed"
    fi
    
    # Check database connection
    if docker-compose exec -T postgres pg_isready -U kyc_user > /dev/null 2>&1; then
        print_status "✅ Database is healthy"
    else
        print_error "❌ Database health check failed"
    fi
    
    # Check RabbitMQ
    if curl -f http://localhost:15672 > /dev/null 2>&1; then
        print_status "✅ RabbitMQ is healthy"
    else
        print_error "❌ RabbitMQ health check failed"
    fi
}

# Main execution
main() {
    print_section "KYC Microservice Setup"
    
    check_dependencies
    create_directories
    create_env_file
    download_models
    create_nginx_config
    create_grafana_dashboards
    start_services
    setup_storage
    run_migrations
    health_check
    show_service_urls
    
    echo -e "\n${GREEN}🎉 KYC Microservice is ready!${NC}"
    echo "View logs with: docker-compose logs -f"
    echo "Stop services with: docker-compose down"
}

# Handle command line arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "start")
        print_status "Starting KYC services..."
        docker-compose up -d
        health_check
        show_service_urls
        ;;
    "stop")
        print_status "Stopping KYC services..."
        docker-compose down
        ;;
    "restart")
        print_status "Restarting KYC services..."
        docker-compose restart
        health_check
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "clean")
        print_warning "This will remove all data and containers. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            docker-compose down -v --remove-orphans
            docker system prune -f
            print_status "System cleaned"
        fi
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup     - Initial setup and start all services (default)"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  logs      - View logs"
        echo "  clean     - Remove all containers and data"
        echo "  help      - Show this help message"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
