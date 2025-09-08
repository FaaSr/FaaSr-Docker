# Stage 1: Build stage
ARG BUILD_FROM
FROM $BUILD_FROM AS build

# Install apt packages
COPY apt-packages.txt /tmp/
RUN apt update && \
    xargs -a /tmp/apt-packages.txt apt install -y && \
    rm /tmp/apt-packages.txt && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt /tmp/
RUN update-ca-certificates \
    && pip install --no-cache-dir --requirement /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Metadata
LABEL description="Base image for FaaSr"
