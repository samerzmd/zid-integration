# Zid Integration Service - AI Coding Assistant Instructions

## Project Overview
FastAPI-based OAuth 2.0 authentication and API integration service for Zid e-commerce platform. Uses Zid's **triple token system** (access_token, Authorization token, refresh_token) with encrypted storage and dual-header authentication pattern.

## Architecture & Core Patterns

### Triple Token Authentication System
- **X-Manager-Token**: Uses `access_token` from OAuth response
- **Authorization Bearer**: Uses `Authorization` field from OAuth response  
- **Refresh Token**: For token renewal (Zid tokens expire in 1 year)
- All tokens encrypted at rest using Fernet encryption with base64 storage

### Key Components
- **OAuthService** (`app/auth/oauth_service.py`): Handles complete OAuth flow with state management
- **TokenManager** (`app/auth/token_manager.py`): Fernet encryption/decryption for tokens
- **ZidAPIClient** (`app/api/zid_client.py`): Authenticated API client with auto-refresh
- **Database Models** (`app/models/database.py`): Encrypted credentials, OAuth states, audit logs

### Database Schema
Three main tables with specific indexing strategy:
- `zid_credentials`: Encrypted tokens with merchant_id unique constraint
- `oauth_states`: CSRF protection with expiry-based cleanup
- `token_audit_logs`: Comprehensive audit trail for all token operations

## Development Patterns

### Environment Configuration
- Uses Pydantic Settings with `.env` file support
- **Critical**: `ENCRYPTION_KEY` must be 32-byte base64 encoded
- Database URLs auto-convert from `postgresql://` to `postgresql+asyncpg://`
- SSL handling for managed databases removes `sslmode` params, adds `ssl='require'`

### Database Operations
```python
# Always use async context manager pattern
async with get_db() as db:
    # Operations here
    await db.commit()  # Auto-handled, but explicit commits in services
```

### API Client Usage
```python
client = ZidAPIClient(merchant_id)
data = await client.get("/orders")  # Auto-handles token refresh
```

### Docker Development Workflow
```bash
# Start full stack
docker-compose up --build

# Run migrations (required after schema changes)
docker-compose --profile migration up migration

# View logs
docker-compose logs -f app
```

## Deployment Patterns

### DigitalOcean App Platform
- Uses `app.yaml` specification with managed PostgreSQL/Redis
- **PRE_DEPLOY** migration job runs `alembic upgrade head`
- Health checks on `/health` endpoint
- Environment variables stored as secrets in DO console

### Database Migrations
- Use Alembic: `alembic revision --autogenerate -m "description"`
- Always include proper indexes for performance
- UUIDs for primary keys, proper foreign key relationships

## Critical Implementation Details

### OAuth Flow Specifics
1. **State Generation**: SHA256 hash with secure random token, stored with expiry
2. **Token Exchange**: Handles both `Authorization` and `authorization` field names from Zid
3. **Error Handling**: Comprehensive logging with merchant_id context
4. **Callback URLs**: Production uses `https://zid-s7xi6.ondigitalocean.app/auth/zid/callback`

### Token Refresh Logic
- Automatic refresh when tokens expire within 30-minute buffer
- Failed refresh attempts logged with IP/user-agent for audit
- Retry logic with exponential backoff for API calls

### Security Considerations
- All tokens encrypted with Fernet before database storage
- OAuth state parameters prevent CSRF attacks
- Comprehensive audit logging for compliance
- Rate limiting follows Zid's 120 requests/minute limit

## Current Phase: Phase 1 Complete
- ✅ OAuth authentication system fully implemented
- ✅ API client with token management working
- ✅ Production deployment on DigitalOcean
- 🚧 **Next**: Phase 2 - Core API Integration (products, orders, customers)

## Testing Approach
- Use `/api/test/{merchant_id}` for API client verification
- `/auth/test-authorize/{merchant_id}` for OAuth flow testing
- `/api/health/{merchant_id}` for token health checks
- Real Zid API testing confirmed working with orders endpoint

## Common Commands
```bash
# Local development
docker-compose up --build
docker-compose --profile migration up migration

# Check specific service logs
docker-compose logs -f app

# Database operations
docker-compose exec app alembic revision --autogenerate -m "description"
docker-compose exec app alembic upgrade head
```

When working on this codebase, always consider the triple token system, encryption requirements, and async database patterns. Follow the established error handling patterns with proper logging context.
