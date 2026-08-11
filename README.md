# Agen MVP

Agen is an autonomous personal-agent platform. A user's private agent understands requests, finds trusted service agents, coordinates approved work, and returns the result.

## Applications

- `backend/`: Django REST API, session authentication, agent identity, and trust ledger
- `frontend/`: Next.js landing page, authentication, personal-agent workspace, and Agent Studio

## Local Setup

### Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

The API runs at `http://localhost:8000`.

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

The web application runs at `http://localhost:3000`.

Use the same hostname for both applications. For example, do not mix `localhost` and `127.0.0.1`, because browser session cookies are hostname-specific.

## Passwordless Authentication Flow

1. The frontend requests a CSRF token from Django.
2. The user enters an email address and Django sends a single-use six-digit code.
3. Successful verification creates the account and personal agent when needed.
4. Django stores the session identifier in an HttpOnly cookie.
5. The protected workspace checks `/api/auth/me/` before rendering.
6. Business agents created in Agent Studio are owned by the authenticated user and persisted in Django.

During local development, the default console email backend prints the code in the Django terminal. For a predictable local code, set `AUTH_DEV_LOGIN_CODE=123456` in `backend/.env`. This setting is ignored whenever `DJANGO_DEBUG=false`. Configure a production email backend before deployment.

## Verification

```powershell
cd backend
python manage.py test apps.accounts apps.agents

cd ..\frontend
npx tsc --noEmit
```
