# Pin to python version to still recieve security updates
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED 1

RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends tini procps net-tools && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*


# Copy in your requirements files
COPY requirements.txt .

# Install dependecies early so they dont get reinstalled all the time
RUN pip3 install -r requirements.txt --no-cache-dir

# make user so we don't run as root.
RUN useradd --create-home appuser
WORKDIR /home/appuser
USER appuser

# Copy your application code to the container (make sure you create a .dockerignore file if any large files or directories should be excluded)
WORKDIR /home/appuser/app/
COPY . .


USER root
RUN pip3 install -e .
USER appuser

CMD mqtt-sn-gateway