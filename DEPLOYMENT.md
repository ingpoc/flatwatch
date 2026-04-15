# Deployment Guide - FlatWatch

## Frontend (Vercel)

1. **Connect Repository**
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New Project"
   - Import your Git repository

2. **Configure Project**
   - Root directory: `frontend/`
   - Framework preset: Next.js
   - Build command: `npm run build`
   - Output directory: `.next`

3. **Environment Variables**

   ```
   NEXT_PUBLIC_API_URL=https://flatwatch-api.onrender.com
   NEXT_PUBLIC_TRUST_API_URL=https://identity-aadhar-gateway-main.onrender.com
   NEXT_PUBLIC_IDENTITY_WEB_URL=https://aadharcha.in
   ```

   Notes:
   - `https://flatwatch.aadharcha.in` uses `frontend/vercel.json` to rewrite same-origin `/api/*` traffic to Render, so the public domain can keep browser requests on the same origin.
   - The deployed auth flow is the demo bearer-token login exposed by `/api/auth/login` and `/api/auth/verify`.

4. **Deploy**
   - Click "Deploy"
   - Vercel will auto-deploy on git push

## Backend (Render)

1. **Create Web Service**
   - Go to [render.com](https://render.com)
   - Click "New" → "Web Service"
   - Connect your Git repository

2. **Configure Service**
   - Root directory: `backend/`
   - Runtime: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables** (set in Render dashboard)

   ```
   SECRET_KEY=your_jwt_secret_here
   ENCRYPTION_KEY=your_32_byte_encryption_key
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Render will deploy at: `https://flatwatch-api.onrender.com`

## Cron Jobs (Render)

1. **Create Cron Job**
   - Go to Render → "New" → "Cron Job"
   - Name: `flatwatch-daily-scan`
   - Command: `curl -X POST https://flatwatch-api.onrender.com/api/scanner/run`
   - Schedule: `0 2 * * *` (2 AM daily)

2. **Email Summaries Cron**
   - Name: `flatwatch-daily-email`
   - Command: `curl -X POST https://flatwatch-api.onrender.com/api/notifications/send/daily`
   - Schedule: `0 8 * * *` (8 AM daily)

## Post-Deployment Checklist

- [ ] Frontend accessible at Vercel URL
- [ ] Backend health check returns 200
- [ ] Database tables created (first request auto-initializes)
- [ ] Test the demo operator login with the seeded backend user
- [ ] Verify CORS settings allow frontend domain
- [ ] Cron jobs scheduled successfully
