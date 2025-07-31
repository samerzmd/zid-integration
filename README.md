# Zid Integration Microservice

A comprehensive FastAPI microservice that integrates with the Zid API to handle OAuth2 authentication, manage merchant tokens, fetch products/orders/stocks, and process webhooks.

## Features

✅ **OAuth2 Integration**
- Authorization Code Flow with Zid
- Secure token storage in PostgreSQL
- Automatic token refresh mechanism

✅ **REST API Endpoints**
- `GET /products` - List product ID, name, price, status
- `GET /products/{product_id}/stock` - Fetch stock information
- `GET /orders` - Return latest 20 orders
- `PATCH /products/{product_id}/price` - Update product pricing
- `GET /health` - Health check endpoint

✅ **Webhook Handling**
- `POST /webhooks/zid` - Handle Zid webhook events
- Support for `order.created`, `product.updated`, `product.stock.updated` events
- Event validation and logging
- Webhook payload storage in PostgreSQL

✅ **Tech Stack**
- Python 3.11+
- FastAPI
- PostgreSQL with SQLAlchemy
- httpx for API calls
- Docker & Docker Compose

## Setup

### 1. Clone and Setup Environment

```bash
git clone <repository>
cd zid-integration
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your Zid app credentials:

```env
DATABASE_URL=postgresql://zid_user:zid_password@localhost:5432/zid_db
ZID_CLIENT_ID=your_zid_client_id
ZID_CLIENT_SECRET=your_zid_client_secret
ZID_REDIRECT_URI=http://localhost:8000/auth/callback
ZID_API_BASE_URL=https://api.zid.sa
SECRET_KEY=your_secret_key_for_jwt_signing
```

### 3. Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose run migrate

# View logs
docker-compose logs -f web
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

## OAuth2 Flow

### 1. Initialize Authorization
```bash
GET /auth/authorize
```
Returns authorization URL to redirect user to Zid

### 2. Handle Callback
```bash
GET /auth/callback?code=AUTH_CODE&state=STATE
```
Exchanges authorization code for access token and stores in database

## API Endpoints

### Products
```bash
# List products
GET /products?merchant_id=MERCHANT_ID&page=1&page_size=20

# Get product stock
GET /products/{product_id}/stock?merchant_id=MERCHANT_ID

# Update product price
PATCH /products/{product_id}/price?merchant_id=MERCHANT_ID
Content-Type: application/json
{
  "price": 99.99
}
```

### Orders
```bash
# List orders (latest 20 by default)
GET /orders?merchant_id=MERCHANT_ID&page=1&page_size=20
```

### Webhooks
```bash
# Webhook endpoint (called by Zid)
POST /webhooks/zid
Content-Type: application/json

# View webhook events
GET /webhooks/events?merchant_id=MERCHANT_ID&event_type=order.created
```

## Supported Webhook Events

- `order.created` - New order placed
- `order.updated` - Order status changed
- `product.updated` - Product information changed
- `product.stock.updated` - Product stock changed

## Database Schema

### MerchantToken
- `id` - Primary key
- `merchant_id` - Unique merchant identifier
- `access_token` - OAuth2 access token
- `refresh_token` - OAuth2 refresh token
- `expires_in` - Token expiration time in seconds
- `created_at` - Token creation timestamp
- `updated_at` - Token last update timestamp

### WebhookEvent
- `id` - Primary key
- `event_type` - Type of webhook event
- `event_id` - Unique event identifier
- `merchant_id` - Associated merchant
- `payload` - JSON webhook payload
- `processed` - Processing status
- `created_at` - Event received timestamp
- `processed_at` - Event processed timestamp

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
alembic upgrade head

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade migration
alembic downgrade -1
```

## Security Considerations

- Store sensitive credentials in environment variables
- Implement proper webhook signature validation
- Use HTTPS in production
- Secure database connections
- Implement rate limiting as needed
- Validate all input data

## Monitoring

The service includes:
- Health check endpoint at `/health`
- Comprehensive logging
- Database query logging (in development)
- Error tracking and reporting

## Deployment

### DigitalOcean App Platform (Recommended)

Deploy to production with one command:

```bash
./deploy.sh
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Local Development

```bash
docker-compose up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Specify your license here]