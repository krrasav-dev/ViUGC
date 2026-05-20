FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV DATABASE_PATH=/app/data/oneliner.db
ENV PORT=5000

EXPOSE 5000

CMD ["python", "wsgi.py"]
