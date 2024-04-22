FROM python:3.11

COPY ./src/django_model_builder/requirements/ /app/requirements/

RUN pip install --upgrade pip pip-tools && \
    pip install -r /app/requirements/requirements.txt

COPY ./src/django_model_builder /app
WORKDIR /app
