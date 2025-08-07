# BASE_IMAGE is the full name of the base image e.g. faasr/base-tidyverse:1.1.2
ARG BASE_IMAGE
# Start from specified base image
FROM $BASE_IMAGE

# Copy invoke functions
COPY faas_specific/faasr_start_invoke_aws.py ${LAMBDA_TASK_ROOT}

#Install R 
RUN dnf install -y R git cmake tar
RUN dnf clean all
RUN Rscript -e "install.packages(c('jsonlite', 'httr'), repos='https://cloud.r-project.org')"

# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is tha name of the user's GitHub repository to install FaaSr from e.g. janedoe/FaaSr-Package-dev
ARG FAASR_INSTALL_REPO

RUN pip install "${FAASR_INSTALL_REPO}@${FAASR_VERSION}"

# Run invoke script
CMD ["faasr_start_invoke_aws.handler"]
