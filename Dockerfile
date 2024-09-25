FROM python:3.12.3-slim-bookworm

WORKDIR /app

COPY requirements*.txt .
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential curl libpq-dev
RUN pip3 install -r requirements.txt
COPY . .

CMD ["python", "main.py"]
