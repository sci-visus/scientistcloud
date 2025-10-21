# ScientistCloud Data Portal - Unified Docker Deployment

This Docker setup allows you to deploy the ScientistCloud Data Portal as an alternative interface on scientistcloud.com, integrating with both your existing VisusDataPortalPrivate and scientistCloudLib systems.

## 🚀 Quick Start

### 1. **Setup Environment**
```bash
cd /Users/amygooch/GIT/ScientistCloud_2.0/SC_Dataportal/SC_Docker
cp env.example .env
# Edit .env with your actual values
```

### 2. **Build and Deploy**
```bash
# Build the containers
docker-compose build

# Start the services
docker-compose up -d

# Check status
docker-compose ps
```

### 3. **Access the Portal**
- **Main Site**: https://scientistcloud.com (existing)
- **Data Portal**: https://scientistcloud.com/portal (new)
- **Health Check**: https://scientistcloud.com/portal/health

## 🏗️ Unified Architecture

### **Existing Systems:**
- **VisusDataPortalPrivate**: Main web application, viewers, database
- **scientistCloudLib**: API, authentication, background services

### **New Portal Integration:**
- **scientistcloud-portal**: PHP/Apache application (port 8080)
- **portal-nginx**: Portal-specific routing (port 8081)
- **Connects to both systems**: Uses existing databases and services
- **No conflicts**: Uses different ports and networks

### **URLs:**
- **Main Site**: `scientistcloud.com/` → VisusDataPortalPrivate system
- **Data Portal**: `scientistcloud.com/portal/` → new portal
- **API**: `scientistcloud.com/portal/api/` → portal API

## 🔧 Configuration

### **Environment Variables:**
Edit `.env` file with your actual values:

```bash
# Database
MONGO_URL=mongodb://mongo:27017
DB_NAME=scientistcloud

# Authentication
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret

# Security
SECRET_KEY=your-secret-key
SECRET_IV=your-secret-iv
```

### **SSL Certificates:**
Place your SSL certificates in the `ssl/` directory:
- `ssl/scientistcloud.com.crt`
- `ssl/scientistcloud.com.key`

## 📊 Monitoring

### **Health Checks:**
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs scientistcloud-portal
docker-compose logs mongo
docker-compose logs nginx

# Check health endpoint
curl https://scientistcloud.com/portal/health
```

### **Database Access:**
```bash
# Connect to MongoDB
docker-compose exec mongo mongosh

# Backup database
docker-compose exec mongo mongodump --out /backup

# Restore database
docker-compose exec mongo mongorestore /backup
```

## 🔄 Deployment Workflow

### **Development:**
```bash
# Make changes to SC_Web/
# Rebuild and restart
docker-compose up --build -d
```

### **Production:**
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up --build -d

# Verify deployment
curl https://scientistcloud.com/portal/health
```

## 🛠️ Troubleshooting

### **Common Issues:**

1. **Port Conflicts:**
   - Portal uses port 8080 (internal)
   - MongoDB uses port 27018
   - Nginx uses ports 80/443

2. **SSL Issues:**
   - Ensure SSL certificates are in `ssl/` directory
   - Check certificate permissions
   - Verify certificate validity

3. **Database Connection:**
   - Check MongoDB container status
   - Verify connection string in `.env`
   - Check network connectivity

4. **Application Errors:**
   - Check application logs: `docker-compose logs scientistcloud-portal`
   - Verify file permissions
   - Check PHP configuration

### **Debug Commands:**
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f

# Access container shell
docker-compose exec scientistcloud-portal bash

# Check nginx configuration
docker-compose exec nginx nginx -t

# Restart specific service
docker-compose restart scientistcloud-portal
```

## 📁 Directory Structure

```
SC_Docker/
├── Dockerfile                 # Portal application container
├── docker-compose.yml         # Service orchestration
├── nginx/                     # Nginx configuration
│   ├── nginx.conf
│   └── conf.d/scientistcloud.conf
├── mongo-init/               # MongoDB initialization
│   └── init.js
├── ssl/                      # SSL certificates
├── logs/                     # Application logs
├── config/                   # Configuration files
└── README.md                 # This file
```

## 🔐 Security

### **Security Headers:**
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000

### **Rate Limiting:**
- API endpoints: 10 requests/second
- Login endpoints: 5 requests/minute

### **SSL/TLS:**
- TLS 1.2+ only
- Strong cipher suites
- HSTS enabled

## 🚀 Production Deployment

### **Prerequisites:**
1. Docker and Docker Compose installed
2. SSL certificates for scientistcloud.com
3. Environment variables configured
4. Domain DNS pointing to server

### **Deployment Steps:**
1. **Clone repository:**
   ```bash
   git clone https://github.com/sci-visus/scientistcloud.git
   cd scientistcloud/SC_Docker
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with production values
   ```

3. **Deploy:**
   ```bash
   docker-compose up -d
   ```

4. **Verify:**
   ```bash
   curl https://scientistcloud.com/portal/health
   ```

## 📞 Support

For issues or questions:
1. Check container logs: `docker-compose logs`
2. Verify configuration files
3. Check network connectivity
4. Review security settings
