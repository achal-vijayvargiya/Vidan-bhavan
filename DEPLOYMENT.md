# Vidhan Bhavan Application - Linux Deployment Guide

## 🚀 Quick Deployment

### Prerequisites
- Linux server with Docker and Docker Compose installed
- At least 4GB RAM and 20GB disk space
- Ports 8000, 5432, and 6379 available

### One-Command Deployment
```bash
# Clone the repository
git clone <your-repo-url>
cd vidanBhavan

# Make deployment script executable and run
chmod +x deploy.sh
./deploy.sh
```

## 📋 Manual Deployment Steps

### 1. Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
```

### 2. Clone and Setup
```bash
# Clone repository
git clone <your-repo-url>
cd vidanBhavan

# Create environment file
cp .env.example .env
# Edit .env with your configuration
nano .env
```

### 3. Deploy Application
```bash
# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
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
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys (add your actual keys)
OPENAI_API_KEY=your-openai-api-key
GOOGLE_GENAI_API_KEY=your-google-genai-api-key
```

### Sensitive Configuration Files
The following files are automatically ignored by `.gitignore`:
- `app/config/gcp_config.json`
- `app/config/gcp_config_bck.json`
- `app/config/OpenRouter.py`
- `.env`

**Important**: Create these files with your actual API keys and credentials before deployment.

## 📊 Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Backend API   │    │   PostgreSQL    │    │     Redis       │
│   (Port 8000)   │◄──►│   (Port 5432)   │    │   (Port 6379)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Services
- **Backend**: FastAPI application with OCR and AI capabilities
- **PostgreSQL**: Primary database for application data
- **Redis**: Caching layer for LLM responses and session data

## 🔍 Monitoring and Health Checks

### Health Check Endpoints
- **Application Health**: `http://your-server:8000/api/health`
- **API Documentation**: `http://your-server:8000/docs`
- **Alternative Docs**: `http://your-server:8000/redoc`

### Service Status Commands
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis

# Check resource usage
docker stats
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Services Not Starting
```bash
# Check if ports are in use
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :5432
sudo netstat -tulpn | grep :6379

# Kill processes using ports if needed
sudo kill -9 <PID>
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Access PostgreSQL directly
docker-compose exec postgres psql -U postgres -d vidhan-pg
```

#### 3. Redis Connection Issues
```bash
# Check Redis logs
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

#### 4. Application Errors
```bash
# Check application logs
docker-compose logs backend

# Restart application
docker-compose restart backend
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Scale application (if needed)
docker-compose up -d --scale backend=2
```

## 🔄 Updates and Maintenance

### Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup Database
```bash
# Create backup
docker-compose exec postgres pg_dump -U postgres vidhan-pg > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U postgres vidhan-pg < backup.sql
```

### Clean Up
```bash
# Remove unused containers and images
docker system prune -a

# Remove volumes (WARNING: This will delete all data)
docker-compose down -v
```

## 🔒 Security Considerations

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 8000/tcp  # Application
sudo ufw allow 22/tcp     # SSH
sudo ufw enable
```

### SSL/HTTPS Setup
```bash
# Install Nginx and Certbot
sudo apt install nginx certbot python3-certbot-nginx

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/vidhan-bhavan
```

### Regular Maintenance
- Update system packages monthly
- Monitor disk space and logs
- Rotate logs regularly
- Backup database weekly

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Verify configuration: `docker-compose config`
3. Check service health: `docker-compose ps`
4. Review this documentation

## 🎯 Production Checklist

- [ ] Docker and Docker Compose installed
- [ ] Environment variables configured
- [ ] Sensitive files created with actual credentials
- [ ] Firewall configured
- [ ] SSL certificate installed (if using HTTPS)
- [ ] Database backup strategy in place
- [ ] Monitoring and logging configured
- [ ] Health checks passing
- [ ] Application accessible via browser

---

**Happy Deploying! 🚀** 