# Stage 1: Build stage
ARG BASE_IMAGE
FROM $BASE_IMAGE

# Create action directory
RUN mkdir -p /action

# Copy invocation scripts
COPY faasr_entry.py /action/exec
RUN chmod +x /action/exec

# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is tha name of the user's GitHub repository to install FaaSr from e.g. janedoe/FaaSr-Package-dev
ARG FAASR_INSTALL_REPO

RUN pip install --no-cache-dir "git+https://github.com/${FAASR_INSTALL_REPO}.git@${FAASR_VERSION}"

# Setup port
ENV FLASK_PROXY_PORT=8080

# Set environment variable for platform
ENV FAASR_PLATFORM="openwhisk"

# Openwhisk actionProxy
RUN mkdir -p /actionProxy/owplatform
RUN git clone https://github.com/apache/openwhisk-runtime-docker 
RUN cp openwhisk-runtime-docker/core/actionProxy/actionproxy.py /actionProxy
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/__init__.py /actionProxy/owplatform
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/knative.py /actionProxy/owplatform
RUN cp openwhisk-runtime-docker/core/actionProxy/owplatform/openwhisk.py /actionProxy/owplatform

# Run actionProxy to listen for requests
CMD ["bin/bash", "-c", "cd actionProxy && ls && python3 -m actionproxy"]

# Metadata
LABEL description="Docker image for FaaSr-py on ow"
