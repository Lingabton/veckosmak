FROM python:3.12-slim

WORKDIR /app

# Install build dependencies for reportlab (needs C compiler for some extensions)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build deps to keep image small
RUN apt-get purge -y --auto-remove gcc libc6-dev

COPY backend/ backend/
COPY scripts/ scripts/

COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
