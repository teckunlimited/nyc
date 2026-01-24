# API Security Configuration

This document describes the security measures implemented in the NYC TLC Trip Data API.

## Security Approach

This platform uses **rate limiting** and **CORS protection** rather than API key authentication. This design is intentional:

1. **Public Analytics Use Case** - Serves public NYC trip data with no sensitive user information
2. **Frontend Security Limitation** - API keys in browser JavaScript provide no real security (easily extracted)
3. **Avoiding Complexity** - API keys require backend proxy/BFF, additional deployment, and latency
4. **Rate Limiting Sufficient** - 100 req/min prevents abuse while allowing legitimate access
5. **Standard Pattern** - Common approach for public analytics platforms serving public datasets

**If user-specific access control is needed**, implement session-based authentication with HttpOnly cookies instead of API keys.

---

## Security Features

### 1. Rate Limiting

**Implementation:** SlowAPI (in-memory rate limiting)

**Limits:**
- Data endpoints (`/api/aggregates/*`, `/api/trips`, `/api/zones`): **100 requests/minute per IP**
- Health endpoints (`/`, `/health`): **200 requests/minute per IP**

**Configuration:** Set `RATE_LIMIT_PER_MINUTE` environment variable (default: 100)

**Response when exceeded:**
```json
{
  "error": "Rate limit exceeded: 100 per 1 minute"
}
```

**Protected Endpoints:**
- `/api/aggregates/daily` - 100/min
- `/api/aggregates/summary` - 100/min
- `/api/trips` - 100/min
- `/api/zones` - 100/min
- `/` (root) - 200/min
- `/health` - 200/min

---

### 2. CORS (Cross-Origin Resource Sharing)

**Implementation:** FastAPI CORSMiddleware with simplified configuration

**Allowed Origins:**
- **All origins** (`*`) for public analytics API
- Configurable via `CORS_ORIGINS` environment variable for additional restrictions

**Configuration:**
```bash
# Allow all origins (current default)
CORS_ORIGINS=*

# Restrict to specific origins
CORS_ORIGINS=http://localhost:4200,https://your-domain.com
```

**Allowed Methods:** GET, POST, PUT, DELETE, OPTIONS  
**Allowed Headers:** Authorization, Content-Type

---

### 3. HTTPS/TLS

- Azure Container Apps provide automatic HTTPS endpoints
- All traffic encrypted in transit
- HTTP requests automatically redirected to HTTPS

---

### 4. Database Security

- Connection pooling with SQLAlchemy
- Parameterized queries prevent SQL injection
- Connection strings stored in Azure Key Vault (production)
- SSL mode required for Azure PostgreSQL connections

---

## Configuration

### Local Development

Create `.env` file in `backend/` directory:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require

# CORS - comma-separated origins or * for all
CORS_ORIGINS=http://localhost:4200,http://localhost:3000

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Environment
ENVIRONMENT=development
```

### Azure Production

Set environment variables in Container Apps:

```bash
az containerapp update \
  --name nyc-backend \
  --resource-group nyc-prod-rg \
  --set-env-vars \
    "CORS_ORIGINS=*" \
    "RATE_LIMIT_PER_MINUTE=100" \
    "ENVIRONMENT=production"
```

---

## Monitoring

### Rate Limit Monitoring

Monitor logs for rate limit violations:

```
INFO:slowapi:Rate limit exceeded for IP 203.0.113.42: 100 per minute
```

### CORS Monitoring

Monitor for CORS errors in browser console and backend logs:

```
WARNING:fastapi:CORS request from unauthorized origin: https://malicious-site.com
```

---

## Testing Security

### Test Rate Limiting

```bash
# Install Apache Bench
brew install httpd  # macOS

# Send 150 requests (expect ~100 success, ~50 rate limited)
ab -n 150 -c 10 http://localhost:8000/api/aggregates/daily
```

### Test CORS

```bash
# Valid origin (should succeed)
curl -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/aggregates/daily

# Invalid origin (with CORS restrictions enabled)
curl -H "Origin: https://evil-site.com" \
  -H "Access-Control-Request-Method: GET" \
  -X OPTIONS http://localhost:8000/api/aggregates/daily
```

### Test Import

```bash
cd backend
python3 -c "from main import app; print('API imports successfully')"
```

---

## Implementation Details

### Files Modified

**backend/requirements.txt:**
- Added `slowapi==0.1.9`

**backend/main.py:**
- Imported SlowAPI components
- Initialized Limiter with IP-based key function
- Added `@limiter.limit()` decorators to all endpoints
- Configured CORS middleware with `allow_origins=["*"]`
- Added `Request` parameter to rate-limited endpoints

**backend/.env.example:**
- Added `CORS_ORIGINS` configuration
- Added `RATE_LIMIT_PER_MINUTE` documentation

---

## Future Enhancements (Not Implemented)

If requirements change and user-specific access control is needed:

### 1. Session-Based Authentication (Recommended)
- **Time:** ~30 minutes
- **Approach:** HttpOnly cookies with backend sessions
- **Benefits:** Real security without frontend credential exposure
- **Use Case:** User login, personalized dashboards

### 2. API Key Authentication (Not Recommended for Frontend)
- **Time:** 30 minutes
- **Issue:** Requires backend proxy/BFF to hide keys
- **Complexity:** Additional service deployment
- **Use Case:** Only if building backend-to-backend integration

### 3. JWT Bearer Tokens
- **Time:** 1-2 hours
- **Approach:** Token-based authentication
- **Benefits:** Stateless, scalable
- **Use Case:** Microservices, mobile apps

### 4. Azure AD Integration
- **Time:** 2-3 hours
- **Approach:** Microsoft Entra ID OAuth 2.0
- **Benefits:** Enterprise SSO
- **Use Case:** Corporate internal tools

### 5. Redis Backend for Rate Limiting
- **Time:** 30 minutes
- **Benefits:** Scale across multiple API instances
- **Use Case:** High-traffic production deployments

### 6. IP Allowlisting
- **Time:** 30 minutes
- **Benefits:** Restrict to specific IP ranges
- **Use Case:** B2B integrations, internal tools

---

## Best Practices

### Development
- Use `http://localhost:4200` for local Angular dev
- Keep rate limits generous (200/min)
- Test with various origins

### Production
- Use HTTPS URLs only
- Set conservative rate limits (100/min)
- Monitor rate limit violations
- Rotate database credentials regularly
- Use Azure Key Vault for secrets

### CI/CD
- Never commit `.env` files (in `.gitignore`)
- Use GitHub Secrets for sensitive values
- Run security scans (Trivy) before deployment
- Validate CORS configuration in pipeline

---

## Security Posture

**Current Implementation:**
- ✅ Rate limiting prevents abuse
- ✅ CORS protection (configurable)
- ✅ HTTPS encryption
- ✅ SQL injection prevention (parameterized queries)
- ✅ Secure credential storage (Key Vault)
- ✅ No authentication required (public data)

**Production Ready:** Yes - appropriate for public analytics API serving public datasets.

---

## References

- [SlowAPI Documentation](https://slowapi.readthedocs.io/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [Azure Container Apps Security](https://learn.microsoft.com/en-us/azure/container-apps/security-baseline)
