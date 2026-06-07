FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN python -m compileall .

EXPOSE 8000

ENV APP_ENV=production
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8000

CMD ["python", "main.py", "run-server", "--host", "0.0.0.0", "--port", "8000"]
