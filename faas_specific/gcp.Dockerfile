# BASE_IMAGE is the full name of the base image e.g. faasr/base-tidyverse:1.1.2
ARG BASE_IMAGE
# Start from specified base image
FROM $BASE_IMAGE
# Set environment variable for platform
ENV FAASR_PLATFORM="gcp"
# Create runtime directory
RUN mkdir -p /action
# Copy FaaSr invocation code
COPY faasr_entry.py /action/
# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is the name of the user's GitHub repository to install FaaSr from e.g. janedoe/FaaSr-Package-dev
ARG FAASR_INSTALL_REPO
RUN pip install --no-cache-dir "git+https://github.com/${FAASR_INSTALL_REPO}.git@${FAASR_VERSION}"
# Install required packages for GCP auth
RUN pip install cryptography requests google-cloud-secret-manager
# GCP specific workdir
WORKDIR /action
CMD ["python3", "faasr_entry.py"]
