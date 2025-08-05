#!/bin/bash

# Vidhan Bhavan Application Deployment Script
# For Linux Server Deployment

set -e  # Exit on any error

echo "🚀 Starting Vidhan Bhavan Application Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Dependencies check passed!"
}

# Create necessary directories and files
setup_environment() {
    print_status "Setting up environment..."
    
    # Create logs directory
    mkdir -p logs
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_warning "Creating .env file from template..."
        cat > .env << EOF
# Application Configuration
ENVIRONMENT=production
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/vidhan-pg

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
EOF
        print_status ".env file created successfully!"
    else
        print_status ".env file already exists"
    fi
}

# Build and start the application
deploy_application() {
    print_status "Building and starting application..."
    
    # Stop existing containers
    docker-compose down
    
    # Build the application
    print_status "Building Docker images..."
    docker-compose build --no-cache
    
    # Start the application
    print_status "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    if docker-compose ps | grep -q "healthy"; then
        print_status "All services are healthy!"
    else
        print_warning "Some services may not be healthy. Check with: docker-compose ps"
    fi
}

# Display deployment information
show_deployment_info() {
    print_status "Deployment completed!"
    echo ""
    echo "📊 Application Status:"
    docker-compose ps
    echo ""
    echo "🌐 Application URLs:"
    echo "   - Backend API: http://localhost:8000"
    echo "   - API Documentation: http://localhost:8000/docs"
    echo "   - Health Check: http://localhost:8000/api/health"
    echo ""
    echo "📝 Useful Commands:"
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop services: docker-compose down"
    echo "   - Restart services: docker-compose restart"
    echo "   - Update application: ./deploy.sh"
    echo ""
}

# Main deployment function
main() {
    print_status "Starting deployment process..."
    
    check_dependencies
    setup_environment
    deploy_application
    show_deployment_info
    
    print_status "Deployment completed successfully! 🎉"
}

# Run main function
main "$@" 