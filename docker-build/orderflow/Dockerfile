FROM python:3.13-slim

WORKDIR /usr/src/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN pip install --upgrade pip --no-cache-dir "poetry==2.1.2"
RUN poetry config virtualenvs.create false

COPY pyproject.toml ./
RUN poetry install

RUN mkdir -p /home/app

RUN addgroup --system app && adduser --system --no-create-home --group app && \
     chown -R app:app /home && chmod -R 755 /home

USER app

ENV APP_HOME=/home/app
WORKDIR $APP_HOME

COPY ./app/entrypoint.sh .
COPY --chown=app ./app $APP_HOME
RUN chmod +x  $APP_HOME/entrypoint.sh

RUN python manage.py collectstatic --noinput

ENTRYPOINT ["/home/app/entrypoint.sh"]