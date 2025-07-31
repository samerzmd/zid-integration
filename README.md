# Zid Integration Service

A FastAPI-based OAuth 2.0 authentication and API integration service for the Zid e-commerce platform.

## Features

- 🔐 Secure OAuth 2.0 flow with Zid's triple token system
- 🐳 Dockerized development environment
- 🌊 DigitalOcean App Platform ready
- 📊 PostgreSQL with async support
- ⚡ Redis for caching and sessions
- 🔄 Database migrations with Alembic
- 🧪 Testing with pytest
- 📝 API documentation with FastAPI

## Quick Start

### Local Development with Docker

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd zid-integration
   cp .env.example .env
   ```

2. **Configure environment**:
   Edit `.env` file with your Zid OAuth credentials:
   ```env
   ZID_CLIENT_ID=your_client_id
   ZID_CLIENT_SECRET=your_client_secret
   ZID_REDIRECT_URI=http://localhost:8000/auth/callback
   ENCRYPTION_KEY=your_32_byte_base64_key
   ```

3. **Start with Docker**:
   ```bash
   docker-compose up --build
   ```

4. **Run migrations**:
   ```bash
   docker-compose --profile migration up migration
   ```

5. **Access the service**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### DigitalOcean App Platform Deployment

1. **Prepare repository**: Push to GitHub
2. **Create App**: Use `app.yaml` specification
3. **Configure databases**: PostgreSQL and Redis managed databases
4. **Set environment variables**: In DO console
5. **Deploy**: Automatic from GitHub

## Project Structure

```
zid-integration/
├── app/
│   ├── auth/           # Authentication services
│   ├── routers/        # API endpoints
│   ├── services/       # Business logic
│   ├── models/         # Database models
│   ├── utils/          # Utilities
│   └── main.py         # FastAPI application
├── alembic/            # Database migrations
├── scripts/            # Initialization scripts
├── tests/              # Test suite
├── docker-compose.yml  # Local development
├── Dockerfile          # Container definition
├── app.yaml           # DigitalOcean config
└── requirements.txt   # Dependencies
```

## Development Status

### ✅ Phase 0: Infrastructure Setup
- [x] Docker environment with PostgreSQL and Redis
- [x] DigitalOcean App Platform configuration
- [x] Project structure and dependencies
- [x] Basic FastAPI application

### 🚧 Phase 1: Authentication System (Next)
- [ ] Database models and migrations
- [ ] OAuth 2.0 service implementation
- [ ] Token management and encryption
- [ ] Authentication endpoints

### 📋 Phase 2: API Integration (Planned)
- [ ] Zid API client
- [ ] Product management endpoints
- [ ] Order management endpoints
- [ ] Customer management endpoints

### 📋 Phase 3: Webhook System (Planned)
- [ ] Webhook endpoints
- [ ] Event processing
- [ ] Queue management

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ZID_CLIENT_ID` | Zid OAuth client ID | Yes |
| `ZID_CLIENT_SECRET` | Zid OAuth client secret | Yes |
| `ZID_REDIRECT_URI` | OAuth callback URL | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `ENCRYPTION_KEY` | 32-byte key for token encryption | Yes |
| `ENV` | Environment (development/production) | No |
| `LOG_LEVEL` | Logging level | No |

## Commands

### Development
```bash
# Start services
docker-compose up

# Run migrations
docker-compose --profile migration up migration

# Run tests (when implemented)
docker-compose exec app pytest

# View logs
docker-compose logs -f app
```

### Database
```bash
# Create migration
docker-compose exec app alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec app alembic upgrade head

# Rollback migration
docker-compose exec app alembic downgrade -1
```

## Contributing

1. Follow the project plan in `PROJECT_PLAN.md`
2. Create feature branches
3. Write tests for new functionality
4. Update documentation
5. Submit pull requests

## License

[Add your license here]