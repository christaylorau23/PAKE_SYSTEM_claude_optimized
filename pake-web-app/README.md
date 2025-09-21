# PAKE System Web Application

A simplified web interface for the PAKE System enterprise knowledge management platform, deployed on Vercel.

## Features

- **RESTful API**: Complete API endpoints for PAKE System functionality
- **Interactive Documentation**: Swagger UI and ReDoc documentation
- **Health Monitoring**: System health and status endpoints
- **Knowledge Search**: AI-powered knowledge search capabilities
- **Content Analysis**: AI content analysis and insights
- **Service Discovery**: List and monitor PAKE System services

## API Endpoints

### Core Endpoints
- `GET /` - Main landing page with system overview
- `GET /health` - System health check
- `GET /system` - System information and features
- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - ReDoc API documentation

### Knowledge Management
- `GET /api/v1/search?query={query}&limit={limit}` - Search knowledge base
- `POST /api/v1/analyze` - AI content analysis
- `GET /api/v1/services` - List available services

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python api.py
```

### Vercel Deployment
```bash
# Deploy to Vercel
vercel --prod
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PAKE_ENV` | Environment mode | `production` |
| `DEBUG` | Debug mode | `false` |

## API Usage Examples

### Health Check
```bash
curl https://your-app.vercel.app/health
```

### Knowledge Search
```bash
curl "https://your-app.vercel.app/api/v1/search?query=AI&limit=5"
```

### Content Analysis
```bash
curl -X POST https://your-app.vercel.app/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Your content to analyze"}'
```

## Response Format

All API responses follow a consistent format:

```json
{
  "data": {...},
  "status": "success",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Handling

The API includes comprehensive error handling:
- `404` - Endpoint not found
- `500` - Internal server error
- `422` - Validation error

## Security

- CORS enabled for cross-origin requests
- Input validation with Pydantic models
- Error handling without exposing sensitive information

## Monitoring

- Health check endpoint for uptime monitoring
- System information endpoint for status checks
- Service discovery for monitoring individual components

## Development

This is a simplified version of the full PAKE System designed for easy deployment and testing. The full enterprise version includes:

- Multi-tenant architecture
- Advanced authentication
- Real-time WebSocket connections
- Complex AI processing pipelines
- Enterprise security features

## License

Part of the PAKE System enterprise platform.
