.PHONY: requirements
RUN := docker compose run --rm web

requirements:
	$(RUN) pip-compile -o /app/requirements/requirements.txt pyproject.toml

collectstatic:
	$(RUN) python manage.py collectstatic

makemigrations:
	$(RUN) python manage.py makemigrations

migrate:
	$(RUN) python manage.py migrate
