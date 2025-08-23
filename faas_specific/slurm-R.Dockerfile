# BASE_IMAGE is the full name of the base image e.g. faasr/base-tidyverse:1.1.2
ARG BASE_IMAGE
# Start from specified base image
FROM $BASE_IMAGE

# Create runtime directory
RUN mkdir -p /action

# Copy FaaSr invocation code
COPY faasr_start_invoke_slurm.py /action/

# Install R
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        r-base && \
    ln -s /usr/bin/Rscript /usr/local/bin/Rscript && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN Rscript -e "install.packages(c('jsonlite', 'httr'), repos='https://cloud.r-project.org')"

# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is the name of the user's GitHub repository to install FaaSr from e.g. janedoe/FaaSr-Package-dev
ARG FAASR_INSTALL_REPO

RUN pip install --no-cache-dir "git+https://github.com/${FAASR_INSTALL_REPO}.git@${FAASR_VERSION}"

# Install required packages for SLURM auth
RUN pip install requests pyjwt

# SLURM specific workdir
WORKDIR /action

CMD ["python3", "faasr_start_invoke_slurm.py"]
