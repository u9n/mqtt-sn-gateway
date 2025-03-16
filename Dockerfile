# Pin to python version to still recieve security updates
FROM python:3.13-slim-bookworm as compile-image

ENV PYTHONUNBUFFERED 1

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends tini procps net-tools && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Create a venv
RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# Copy in your requirements files
COPY requirements.txt .

# Install dependecies early so they dont get reinstalled all the time
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt --no-cache-dir


WORKDIR /opt/app/
COPY . .

RUN pip3 install .

# Compile image has now installed a full virtual environment that we can copy to the
# build image
# -----------
FROM python:3.13-slim-bookworm as build-image

# Apply security upgrades, install some nice to have and clean up afterwards
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends tini procps net-tools && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Copy in the venv from the compile image
COPY --from=compile-image /opt/venv /opt/venv

# Use the venv copied over
ENV PATH="/opt/venv/bin:$PATH"

# make user so we don't run as root.
RUN useradd --create-home appuser
WORKDIR /home/appuser
USER appuser

# Copy your application code to the container (make sure you create a .dockerignore file if any large files or directories should be excluded)
WORKDIR /home/appuser/app/

CMD mqtt-sn-gateway