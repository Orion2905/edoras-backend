# Edoras Flask API

Flask backend per l'applicazione Edoras con architettura API RESTful.

🚀 **Deploy Status**: Ready for Azure App Service

## Struttura Flask

```
backend/
├── src/
│   ├── app/                    # Applicazione Flask principale
│   │   ├── __init__.py        # App factory
│   │   ├── api/               # API endpoints
│   │   │   ├── __init__.py
│   │   │   └── v1/            # API versione 1
│   │   │       ├── __init__.py
│   │   │       ├── auth.py    # Autenticazione endpoints
│   │   │       ├── users.py   # User management
│   │   │       └── health.py  # Health check
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── base.py
│   │   ├── schemas/           # Marshmallow schemas
│   │   │   ├── __init__.py
│   │   │   └── user.py
│   │   ├── services/          # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   └── user_service.py
│   │   ├── utils/             # Utility functions
│   │   │   ├── __init__.py
│   │   │   ├── decorators.py
│   │   │   └── helpers.py
│   │   └── extensions/        # Flask extensions
│   │       ├── __init__.py
│   │       ├── database.py
│   │       └── jwt.py
│   ├── config/               # Configurazioni
│   │   ├── __init__.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   └── migrations/           # Database migrations (Alembic)
├── tests/                    # Test suite
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── requirements.txt          # Dipendenze Python
├── requirements-dev.txt      # Dipendenze sviluppo
├── app.py                   # Entry point
├── .env.example             # Template environment variables
└── Dockerfile               # Container Docker
```

## Setup Rapido

1. **Crea virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate   # Windows
   ```

2. **Installa dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura environment:**
   ```bash
   cp .env.example .env
   # Modifica .env con le tue configurazioni
   ```

4. **Inizializza database:**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. **Start development server:**
   ```bash
   flask run --debug
   ```

## API Endpoints

Base URL: `http://localhost:5000/api/v1`

### Autenticazione
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `POST /api/v1/auth/logout` - User logout

### Users
- `GET /api/v1/users` - Lista utenti (admin)
- `GET /api/v1/users/me` - Profilo utente corrente
- `PUT /api/v1/users/me` - Aggiorna profilo
- `DELETE /api/v1/users/me` - Elimina account

### Health
- `GET /api/v1/health` - Health check
- `GET /api/v1/health/db` - Database health

## Testing

```bash
# Run tutti i test
pytest

# Run con coverage
pytest --cov=src

# Run test specifici
pytest tests/unit/test_users.py
```

## Deployment

```bash
# Build per produzione
pip freeze > requirements.txt

# Deploy su Azure
../../scripts/deploy.sh
```

## Tecnologie

- **Flask** - Web framework
- **SQLAlchemy** - ORM
- **Marshmallow** - Serializzazione/validazione
- **Flask-JWT-Extended** - JWT authentication
- **Flask-CORS** - CORS support
- **Flask-Migrate** - Database migrations
- **Pytest** - Testing framework
# Test deployment with publish profile
# Deploy with fresh publish profile
# Test deployment with correct publish profile
# edoras-backend
