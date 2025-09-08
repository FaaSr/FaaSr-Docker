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

# Install Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    ln -s /usr/bin/python3 /usr/local/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VENV=/opt/venv
RUN python3 -m venv $VENV
ENV PATH="$VENV/bin:$PATH"

# Install Python packages
COPY requirements.txt /tmp/
RUN update-ca-certificates && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install cran packages
COPY R_packages.R /tmp/
RUN Rscript /tmp/R_packages.R && \
    rm /tmp/R_packages.R && \
    rm -rf /tmp/downloaded_packages/ /tmp/*.rds /tmp/*.tar.gz

# Metadata
LABEL description="Base image for FaaSr -- R from Rocker"