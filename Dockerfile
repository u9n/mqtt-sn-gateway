# Pin to python version to still receive security updates from refreshed base images.
FROM python:3.13-slim-bookworm AS compile-image

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install build dependencies only in the compile stage. Avoid apt-get upgrade here:
# scheduled rebuilds already pull a refreshed base image, and upgrades can fail on
# transient Debian mirror/package index mismatches.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Create a venv
RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# Copy in your requirements files
COPY requirements.txt .

# Install dependencies early so they don't get reinstalled all the time
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

WORKDIR /opt/app/
COPY . .

RUN pip install .

# Compile image has now installed a full virtual environment that we can copy to the
# build image
# -----------
FROM python:3.13-slim-bookworm AS build-image

# Install runtime tools and clean up afterwards. Avoid apt-get upgrade for the
# same mirror-stability reason as above.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y --no-install-recommends tini procps net-tools && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Copy in the venv from the compile image
COPY --from=compile-image /opt/venv /opt/venv

# Use the venv copied over
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1

# make user so we don't run as root.
RUN useradd --create-home appuser
WORKDIR /home/appuser/app/
USER appuser

CMD ["mqtt-sn-gateway"]
