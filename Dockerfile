FROM openstax/postgres:9.4

RUN apt-get update

# Install build dependencies
RUN set -x \
    && apt-get update \
    && apt-get install build-essential pkg-config git python-pip --no-install-recommends -y \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install the 'plpython' extension language
RUN set -x \
    && apt-get update \
    && apt-get install python-dev postgresql-plpython-$PG_MAJOR --no-install-recommends -y 
# Install the 'plxslt' extension language
RUN set -x \
    && apt-get update \
    && apt-get install libxml2-dev libxslt-dev zlib1g-dev postgresql-server-dev-$PG_MAJOR --no-install-recommends -y \
    && git clone https://github.com/petere/plxslt.git \
    && cd plxslt \
    && make \
    && make install

# Upgrade pip and packaging tools
RUN set -x \
    && pip install -U pip setuptools wheel \
    && apt remove python-pip -y

COPY requirements /tmp/requirements

# Copy the project into the container
COPY . /src/
WORKDIR /src/

RUN set -x \
    && pip install -r /tmp/requirements/test.txt \
    && pip install -r /tmp/requirements/deploy.txt \
                   -r /tmp/requirements/main.txt \
    && pip uninstall -y cnx-db || echo "cnx-db is not installed, continuing..." \
    && pip install -e . \
    && find /usr/local -type f -name '*.pyc' -name '*.pyo' -delete \
    && rm -rf ~/.cache/

EXPOSE 5432

# This is a specially created user for non-superuser operations.
ENV DB_USER=rhaptos

ENV POSTGRES_DB=repository

# These are used by this codebase's tools (e.g. `cnxdb init`).
ENV DB_URL=postgresql://rhaptos@/repository
ENV DB_SUPER_URL=postgresql://rhaptos_admin@/repository

# This is a hook into the postgres:* container to do database init
COPY .dockerfiles/initdb.d/* /docker-entrypoint-initdb.d/

# Use PIP_FIND_LINKS environment variable to point to specific packages
#   (e.g. PIP_FIND_LINKS="https://packages.cnx.org/dist/")
# ENV PIP_FIND_LINKS ...
