FROM docker.io/library/python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY python-brain/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY python-brain/*.py ./python-brain/

USER 10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "api:app", "--app-dir", "python-brain", "--host", "0.0.0.0", "--port", "8080"]
