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

# Install R packages
COPY R_packages.R /tmp/
RUN Rscript /tmp/R_packages.R && \
    rm /tmp/R_packages.R && \
    rm -rf /tmp/downloaded_packages/ /tmp/*.rds /tmp/*.tar.gz

# Stage 2: Runtime stage
FROM build as runtime

# Create function directory
RUN mkdir -p /lambda_runtime /action

# Copy FaaSr invocation code
COPY faasr_start_invoke_helper.R faasr_start_invoke_aws-lambda.R faasr_start_invoke_github-actions.R /action/

# Copy Python wrapper
COPY python_wrapper_aws-lambda.py /lambda_runtime/lambda_function.py

# Install AWS Lambda Runtime Interface Emulator
RUN curl -Lo /usr/bin/aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie && \
    chmod +x /usr/bin/aws-lambda-rie
COPY entrypoint_aws-lambda.sh /lambda_runtime/entry.sh
RUN chmod +x /lambda_runtime/entry.sh

# Setup port
ENV FLASK_PROXY_PORT 8080

# Copy and make files/directories for actionProxy
RUN mkdir -p /actionProxy/owplatform
RUN git clone https://github.com/apache/openwhisk-runtime-docker
RUN cp openwhisk-runtime-docker/core/actionProxy/actionproxy.py /actionProxy
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/__init__.py /actionProxy/owplatform
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/knative.py /actionProxy/owplatform
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/openwhisk.py /actionProxy/owplatform

# Setup basic executable
# Copy FaaSr invocation code
COPY faasr_start_invoke_openwhisk.R /action/exec
RUN chmod +x /action/exec

# Add json schema
ADD https://raw.githubusercontent.com/FaaSr/FaaSr-package/main/schema/FaaSr.schema.json /action/

# Metadata
LABEL maintainer="Renato Figueiredo <renato [at] ece.ufl.edu>"
LABEL description="Docker image for FaaSr"
