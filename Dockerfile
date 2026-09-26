FROM node:20-alpine AS webapp
WORKDIR /webapp
COPY webapp/package*.json ./
RUN npm install
COPY webapp/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=webapp /webapp/dist ./webapp/dist
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]