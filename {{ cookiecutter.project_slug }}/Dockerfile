# For appliku.com usage only. For more details about why /code/ and /env/ see
# https://appliku.com/post/using-custom-dockerfile-appliku

# ----------------------------------------------------------------------------
# Django app
# ----------------------------------------------------------------------------
FROM python:3.11
SHELL ["/bin/bash", "-c"]

# Needed for django's compilemessages
RUN apt-get update && apt-get install -y gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code/

# Allow statements and log messages to immediately appear in the container logs
ENV PYTHONUNBUFFERED True

# Install static part of python modules
RUN pip install poetry
RUN poetry config virtualenvs.in-project true
COPY /code/pyproject.toml /code/
COPY /code/poetry.lock /code/
RUN poetry install --only main --no-root

# Copy over compiled client
# COPY --from=builder /code/dist /code/dist

# Copy source
COPY /code/ /code/
COPY /env/ /env/

# MUST have an .env file
RUN touch /code/.env

# Collect static files and i18n
RUN source /env/envs_export.sh && export && cd /code/ && \
    poetry run python ./manage.py collectstatic
RUN source /env/envs_export.sh && export && cd /code/ && \
    poetry run python manage.py compilemessages --locale=de --locale=fr --locale=it

RUN useradd -ms /bin/bash code

USER code

# Fix dubious ownership in repository warning
RUN git config --global --add safe.directory /code
