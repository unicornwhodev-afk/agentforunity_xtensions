FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
	git \
	&& rm -rf /var/lib/apt/lists/*

COPY ./setup-train-runpod/requirements-prep.txt /tmp/requirements-prep.txt
RUN pip install --no-cache-dir -r /tmp/requirements-prep.txt

COPY ./setup-train-runpod/prepare_dataset.py /app/prepare_dataset.py

CMD ["python", "/app/prepare_dataset.py", "--help"]
