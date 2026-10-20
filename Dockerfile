# Krypton as a container: runs on any host that runs Docker (Google Cloud Run, Render, Railway, Fly.io, AWS...).
# Hosts can start as many copies as they need for the number of visitors; every copy shares the same
# database (DATABASE_URL), and the 9-day login cookie keeps people logged in whichever copy they reach.
#
# Secrets are given to the host as environment variables (never put them in this file):
#   DATABASE_URL, ANTHROPIC_API_KEY, STRIPE_SECRET_KEY, STRIPE_PRICE_ID, APP_URL
FROM python:3.14-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Online mode: never fall back to a temporary local database (see storage.py)
ENV KRYPTON_ONLINE=1 \
    PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8080') + '/_stcore/health')"
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
