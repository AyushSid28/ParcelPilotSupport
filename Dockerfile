FROM node:20-alpine AS web
WORKDIR /web
COPY web/package.json ./
RUN npm install
COPY web ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend ./backend
COPY data/source ./data/source
COPY --from=web /web/dist ./web/dist
RUN pip install --no-cache-dir ./backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
