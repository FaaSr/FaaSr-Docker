# BASE_IMAGE is the full name of the base image e.g. faasr/base-tidyverse:1.1.2
ARG BASE_IMAGE
# Start from specified base image
FROM $BASE_IMAGE as build

#Install R 
RUN dnf install -y \
    R R-core R-devel \
    gcc gcc-c++ gfortran make tar gzip \
    unzip patch which git pkgconf binutils file \
    libcurl-devel openssl-devel \
    zlib-devel libxml2-devel pcre2-devel \
    && dnf clean all

# Install CRAN packages 
COPY faas_specific/R_packages.R /tmp/
RUN Rscript /tmp/R_packages.R && \
    rm /tmp/R_packages.R && \
    rm -rf /tmp/downloaded_packages/ /tmp/*.rds /tmp/*.tar.gz

FROM build as runtime

# Copy invoke functions
COPY faas_specific/faasr_start_invoke_aws.py ${LAMBDA_TASK_ROOT}

# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is tha name of the user's GitHub repository to install FaaSr from e.g. janedoe/FaaSr-Package-dev
ARG FAASR_INSTALL_REPO

RUN pip install "${FAASR_INSTALL_REPO}@${FAASR_VERSION}"

# Run invoke script
CMD ["faasr_start_invoke_aws.handler"]
