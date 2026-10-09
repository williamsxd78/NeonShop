# Auth Testing
- Credentials: /app/memory/test_credentials.md
- POST /api/auth/login {email,password} -> {token,user}; use `Authorization: Bearer <token>`
- GET /api/auth/me returns user (no password_hash)
- users.email unique index; bcrypt hashes start with $2b$
- 5 failed logins per ip:email => 429 for 15 min
