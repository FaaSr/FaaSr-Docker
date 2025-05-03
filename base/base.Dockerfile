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
RUN mkdir -p /lambda_runtime /action

# Copy FaaSr invocation code
# to-do: add entry points for other platforms
COPY faasr_start_invoke_aws-lambda.py faasr_start_invoke_github_actions.py faasr_start_invoke_helper.py /action/

# Add json schema
ADD https://raw.githubusercontent.com/FaaSr/FaaSr-package/main/schema/FaaSr.schema.json /tmp/

# Setup port
ENV FLASK_PROXY_PORT 8080

# Openwhisk actionProxy
RUN mkdir -p /actionProxy/owplatform
RUN git clone https://github.com/apache/openwhisk-runtime-docker
RUN cp openwhisk-runtime-docker/core/actionProxy/actionproxy.py /actionProxy
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/__init__.py /actionProxy/owplatform
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/knative.py /actionProxy/owplatform
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/openwhisk.py /actionProxy/owplatform

COPY faasr_start_invoke_openwhisk.py /action/exec

# Metadata
LABEL description="Docker image for FaaSr-py"
