# Used for Railway (Docker builder) or AWS ECS / Lambda container image
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway polling / ECS
CMD ["python", "main.py"]

# ── AWS Lambda container image ────────────────────────────────────────────────
# Uncomment the two lines below and comment out CMD above when building for Lambda:
# RUN pip install --no-cache-dir awslambdaric
# ENTRYPOINT ["python", "-m", "awslambdaric", "--handler", "lambda_handler.handler"]
