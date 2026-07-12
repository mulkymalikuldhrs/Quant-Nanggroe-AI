# 🚀 Agentic AI System - Deployment Guide

**Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩**

## 📋 Overview

This guide covers deployment of the Agentic AI System across multiple platforms including Railway, Vercel, Netlify, Firebase, AWS, Docker, and Kubernetes.

## 🔧 Prerequisites

### Required Software
- **Python 3.12+**
- **Node.js 18+** (for some deployments)
- **Docker** (for containerized deployments)
- **Git**

### Required Accounts (Choose based on deployment)
- Railway account
- Vercel account
- Netlify account
- Firebase/Google Cloud account
- AWS account
- Docker Hub account

## 🚀 Quick Deployment Options

### 1. Railway (Recommended for Beginners)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

**Configuration**: Uses `railway.json` automatically.

### 2. Vercel (Best for Frontend + Serverless)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel

# Follow prompts and use vercel.json config
```

### 3. Netlify (Great for Static + Functions)

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod

# Uses netlify.toml configuration
```

### 4. Firebase (Google Cloud Integration)

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize
firebase init

# Deploy
firebase deploy
```

### 5. AWS (Enterprise/Scalable)

```bash
# Install AWS CLI and SAM CLI
pip install awscli aws-sam-cli

# Configure AWS credentials
aws configure

# Deploy using SAM
sam build
sam deploy --guided
```

### 6. Docker (Local/Self-hosted)

```bash
# Build image
docker build -t agentic-ai .

# Run locally
docker run -p 5000:5000 agentic-ai

# Or use Docker Compose
docker-compose up -d
```

### 7. Kubernetes (Production Scale)

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s-deployment.yaml

# Check deployment
kubectl get pods -n agentic-ai-system
```

## 🔐 Environment Variables Setup

### Required Variables

Copy `.env.example` to `.env` and configure:

```bash
# System Configuration
FLASK_ENV=production
SECRET_KEY=your-production-secret-key

# Database (Choose one)
DATABASE_URL=postgresql://user:pass@host:5432/db
# OR
DATABASE_URL=sqlite:///data/agentic.db

# Credential Management
CREDENTIAL_MASTER_PASSWORD=your-secure-master-password

# External Services (Optional)
OPENAI_API_KEY=your-openai-key
GITHUB_TOKEN=your-github-token
GOOGLE_CREDENTIALS_PATH=path/to/credentials.json

# Web Automation
SELENIUM_HEADLESS=true
```

### Platform-Specific Variables

#### Railway
- Automatically uses environment variables from dashboard
- Database and Redis provided as services

#### Vercel
```bash
vercel env add SECRET_KEY
vercel env add DATABASE_URL
vercel env add CREDENTIAL_MASTER_PASSWORD
```

#### Netlify
- Set in Netlify dashboard under Site Settings > Environment Variables

#### Firebase
- Configure in Firebase console under Project Settings

#### AWS
- Use AWS Systems Manager Parameter Store or Secrets Manager

## 📊 Database Setup

### PostgreSQL (Recommended for Production)

1. **Create Database**:
```sql
CREATE DATABASE agentic_ai;
CREATE USER agentic_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE agentic_ai TO agentic_user;
```

2. **Set DATABASE_URL**:
```
postgresql://agentic_user:secure_password@host:5432/agentic_ai
```

### SQLite (Development)

Database file will be created automatically at `data/agentic.db`.

## 🔒 Security Configuration

### 1. Credential Management
```bash
# Set a strong master password
export CREDENTIAL_MASTER_PASSWORD="your-very-secure-password-here"

# Ensure data directory permissions
chmod 700 data/
chmod 600 data/credentials.db
```

### 2. Web Automation Security
```bash
# Configure Chrome for headless mode
export SELENIUM_HEADLESS=true
export SELENIUM_TIMEOUT=30
```

### 3. API Keys Security
- Never commit API keys to repository
- Use platform-specific secret management
- Rotate keys regularly

## 🌐 Domain Configuration

### Custom Domain Setup

#### Railway
1. Go to Railway dashboard
2. Navigate to Settings > Domains
3. Add custom domain
4. Configure DNS records

#### Vercel
```bash
vercel domains add yourdomain.com
```

#### Netlify
1. Go to Site Settings > Domain Management
2. Add custom domain
3. Configure DNS

#### Firebase
```bash
firebase hosting:channel:create live
firebase target:apply hosting live your-project-id
```

## 📈 Monitoring Setup

### Health Checks
All deployments include health check endpoint:
```
GET /api/system/status
```

Response:
```json
{
  "status": "healthy",
  "agents": 8,
  "uptime": "2 hours",
  "version": "1.0.0"
}
```

### Logging Configuration

#### Centralized Logging
```bash
# Set log level
export LOG_LEVEL=INFO

# Configure log file
export LOG_FILE_PATH=logs/agentic.log
```

#### Platform-Specific Logging

- **Railway**: Automatic log aggregation
- **Vercel**: Function logs in dashboard
- **Netlify**: Function logs and build logs
- **Firebase**: Cloud Logging integration
- **AWS**: CloudWatch integration

## 🚀 Performance Optimization

### 1. Resource Configuration

#### Memory Requirements
- **Minimum**: 512MB RAM
- **Recommended**: 1GB RAM
- **Optimal**: 2GB+ RAM for AI features

#### CPU Requirements
- **Development**: 0.5 vCPU
- **Production**: 1+ vCPU
- **High Load**: 2+ vCPU

### 2. Caching Strategy

#### Redis Configuration
```bash
# For production deployments
export REDIS_URL=redis://your-redis-host:6379
```

#### In-Memory Caching
```bash
# Enable caching
export ENABLE_CACHING=true
export CACHE_TTL=3600
```

### 3. Database Optimization

#### Connection Pooling
```bash
export DATABASE_POOL_SIZE=10
export DATABASE_MAX_OVERFLOW=20
```

#### Query Optimization
- Enable query logging in development
- Use database indexes for frequent queries
- Implement query caching where appropriate

## 🔄 CI/CD Configuration

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy Agentic AI System

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Deploy to Railway
      uses: railway-deploy@v1
      with:
        railway_token: ${{ secrets.RAILWAY_TOKEN }}
```

### Automated Testing
```bash
# Run tests before deployment
python -m pytest tests/
python -m pytest tests/integration/
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Kill process on port 5000
sudo lsof -ti:5000 | xargs kill -9

# Or use different port
export PORT=8000
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
python -c "from src.core.database import test_connection; test_connection()"
```

#### 3. Selenium WebDriver Issues
```bash
# Install Chrome for headless mode
apt-get update && apt-get install -y google-chrome-stable

# Download ChromeDriver
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
```

#### 4. Memory Issues
```bash
# Check memory usage
free -h

# Increase swap space (Linux)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Platform-Specific Issues

#### Railway
- Check build logs in dashboard
- Verify environment variables
- Ensure proper start command

#### Vercel
- Function timeout limit (10s-30s)
- Cold start issues
- File size limitations

#### Netlify
- Build time limitations
- Function memory limits
- Edge location deployment

#### Firebase
- Quota limitations
- Function execution time
- Firestore security rules

#### AWS
- IAM permissions
- VPC configuration
- Security group rules

#### Docker
- Container resource limits
- Volume mounting issues
- Network connectivity

#### Kubernetes
- Pod resource requests/limits
- Persistent volume claims
- Service discovery

## 📞 Support

### Getting Help

1. **Check logs first**:
   ```bash
   tail -f logs/agentic.log
   ```

2. **Verify system status**:
   ```bash
   curl http://localhost:5000/api/system/status
   ```

3. **Test individual components**:
   ```bash
   python -c "from src.agents.agent_base import AgentBase; print('Agents working')"
   python -c "from src.core.credential_manager import credential_manager; print('Credentials working')"
   ```

### Community

- **Repository**: https://github.com/eemdeexyz/Agentic-AI-System
- **Issues**: Create GitHub issue with detailed description
- **Discussions**: Use GitHub Discussions for questions

### Contact

**Created by Mulky Malikul Dhaher in Indonesia 🇮🇩**

---

## 🎯 Deployment Checklist

Before going to production:

- [ ] Environment variables configured
- [ ] Database setup and tested
- [ ] Security configurations applied
- [ ] Health checks working
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Performance tested
- [ ] Documentation updated
- [ ] Team trained on system

**🇮🇩 Proudly Made in Indonesia - Ready for Global Deployment!**
