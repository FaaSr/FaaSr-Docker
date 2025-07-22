# BASE_IMAGE is the full name of the base image e.g. faasr/base-tidyverse:1.1.2
ARG BASE_IMAGE
# Start from specified base image
FROM $BASE_IMAGE

# Install R
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        r-base \
        r-base-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is tha name of the user's GitHub repository to install FaaSr from e.g. janedoe/FaaSr-Package-dev
ARG FAASR_INSTALL_REPO

RUN pip install "${FAASR_INSTALL_REPO}@${FAASR_VERSION}"

# GitHub Actions specifics
WORKDIR /action

CMD ["python3", "faasr_start_invoke_github-actions.py"]
