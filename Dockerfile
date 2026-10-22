# Pin to python version to still receive security updates from refreshed base images.
FROM python:3.13-slim-bookworm AS compile-image

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies only in the compile stage. Avoid apt-get upgrade here:
# scheduled rebuilds already pull a refreshed base image, and upgrades can fail on
# transient Debian mirror/package index mismatches.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Base images may bundle vulnerable pip. Bootstrap the known-fixed 26.2.2 wheel
# with the SHA-256 from Python's security advisory, then use patched pip to fetch
# the latest release. This pins only the bootstrap, not the final pip version.
RUN /usr/local/bin/python -m pip install --no-deps \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" && \
    /usr/local/bin/python -m pip install --upgrade pip

# ensurepip has its own bundled wheel, unchanged by upgrading global pip.
# Bypass it and let patched global pip install current pip into the empty venv.
RUN /usr/local/bin/python -m venv --without-pip /opt/venv && \
    /usr/local/bin/python -m pip --python /opt/venv install --upgrade pip
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies before copying application code to preserve build caching.
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /opt/app/
COPY . .

RUN python -m pip install .

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

# Remove the unused base-image pip and ensurepip's stale bootstrap wheel offline.
# Keep only the upgraded venv pip, so the runtime cannot seed an insecure venv.
RUN /usr/local/bin/python -m pip --disable-pip-version-check uninstall --yes pip && \
    /usr/local/bin/python -c "import ensurepip, pathlib, shutil; shutil.rmtree(pathlib.Path(ensurepip.__file__).parent)"

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
