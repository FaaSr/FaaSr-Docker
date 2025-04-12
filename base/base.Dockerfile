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

# Stage 2: Runtime stage
FROM build as runtime

# Create function directory
RUN mkdir -p /action

# Copy FaaSr invocation code
# to-do: add entry points for other platforms
COPY faasr_start_invoke_github-actions.py /action/

# Add json schema
ADD https://raw.githubusercontent.com/FaaSr/FaaSr-package/main/schema/FaaSr.schema.json /action/

# Metadata
LABEL description="Docker image for FaaSr-py"
