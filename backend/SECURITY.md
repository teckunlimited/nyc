# API Security Configuration

This document describes the security measures implemented in the NYC TLC Trip Data API.

## Security Features

### 1. Rate Limiting
**Implementation**: SlowAPI (Redis-backed rate limiting)

All API endpoints have rate limiting configured:
- **Data endpoints** (`/api/aggregates/*`, `/api/trips`, `/api/zones`): 100 requests/minute per IP
- **Health/Status endpoints** (`/`, `/health`): 200 requests/minute per IP

**Configuration**: Set in environment variable `RATE_LIMIT_PER_MINUTE` (default: 100)

**Response when limit exceeded**:
```json
{
  "error": "Rate limit exceeded: 100 per 1 minute"
}
```

### 2. CORS (Cross-Origin Resource Sharing)
**Implementation**: FastAPI CORSMiddleware with regex pattern matching

CORS is configured to allow requests from:
1. **Azure Container Apps** (automatic via regex):
   - `https://nyc-dev-frontend.*-*.westus.azurecontainerapps.io`
   - `https://nyc-staging-frontend.*-*.westus.azurecontainerapps.io`
   - `https://nyc-prod-frontend.*-*.westus.azurecontainerapps.io`
   
2. **Additional origins** (via environment variable):

**Development**:
```bash
CORS_ORIGINS=http://localhost:4200,http://localhost:3000
```

**Production** (add custom domains):
```bash
CORS_ORIGINS=http://localhost:4200,https://your-custom-domain.com,https://www.your-domain.com
```

**Important**: If you have custom domains pointing to your frontend, you **must** add them to the `CORS_ORIGINS` environment variable. The regex pattern only matches Azure Container Apps URLs automatically.

**Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS
**Allowed Headers**: Authorization, Content-Type

**Note**: The Azure Container Apps URLs use regex pattern matching to support dynamic hostname segments (e.g., `randomword-abc123`).

### 3. HTTPS/TLS
- Azure Container Apps automatically provide HTTPS endpoints
- All traffic is encrypted in transit
- HTTP requests are automatically redirected to HTTPS

### 4. Database Security
- Connection pooling with SQLAlchemy
- Parameterized queries to prevent SQL injection
- Connection strings stored in Azure Key Vault (production)
- SSL mode required for Azure PostgreSQL connections

## Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require

# CORS - comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:4200,https://your-frontend.azurewebsites.net

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Environment
ENVIRONMENT=production
```

### Azure Configuration

Set environment variables in Azure Container Apps:

```bash
az containerapp update \
  --name nyc-backend \
  --resource-group nyc-prod-rg \
  --set-env-vars \
    "CORS_ORIGINS=https://your-custom-domain.com" \
    "RATE_LIMIT_PER_MINUTE=100" \
    "ENVIRONMENT=production"
```

**Note**: Azure Container Apps frontend URLs are automatically allowed via regex pattern, so you only need to add custom domains to `CORS_ORIGINS`.

## Monitoring

### Rate Limit Monitoring

SlowAPI automatically tracks rate limit violations. Monitor logs for:

```
INFO:slowapi:Rate limit exceeded for IP 203.0.113.42: 100 per minute
```

### CORS Monitoring

Monitor for CORS errors in browser console and backend logs:

```
WARNING:fastapi:CORS request from unauthorized origin: https://malicious-site.com
```

## Testing Security

### Test Rate Limiting

```bash
# Install Apache Bench
brew install httpd  # macOS

# Test rate limiting (send 150 requests)
ab -n 150 -c 10 http://localhost:8000/api/aggregates/daily

# Expected: ~100 success, ~50 rate limited
```

### Test CORS

```bash
# Valid origin (should succeed)
curl -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/aggregates/daily

# Invalid origin (should fail)
curl -H "Origin: https://evil-site.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/aggregates/daily
```

## Future Enhancements

### Planned Security Features (Not Yet Implemented)

1. **API Key Authentication**
   - Add `X-API-Key` header requirement
   - Store keys in Azure Key Vault
   - Rotate keys periodically

2. **JWT Bearer Tokens**
   - User authentication with JWT
   - Token expiration and refresh
   - Role-based access control

3. **Azure AD Integration**
   - Microsoft Entra ID authentication
   - OAuth 2.0 flows
   - Enterprise SSO support

4. **Request Validation**
   - Input sanitization
   - SQL injection prevention (already using parameterized queries)
   - XSS protection

5. **IP Allowlisting**
   - Restrict API access to specific IP ranges
   - Useful for B2B integrations

## Best Practices

### Development
- Use `http://localhost:4200` for local Angular dev server
- Keep rate limits generous during development (200/minute)
- Test with both valid and invalid origins

### Production
- Use HTTPS URLs only in `CORS_ORIGINS`
- Set conservative rate limits (100/minute)
- Monitor rate limit violations
- Rotate database credentials regularly
- Use Azure Key Vault for secrets management

### CI/CD
- Never commit `.env` files to git (already in `.gitignore`)
- Use GitHub Secrets for sensitive values
- Validate CORS configuration in deployment pipeline
- Run security scans (Trivy) before deployment

## References

- [SlowAPI Documentation](https://slowapi.readthedocs.io/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [Azure Container Apps Security](https://learn.microsoft.com/en-us/azure/container-apps/security-baseline)
