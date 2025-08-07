# BASE_IMAGE is the full name of the base image e.g. public.ecr.aws/lambda/python:3.13
ARG BASE_IMAGE
# Start from specified base image
FROM $BASE_IMAGE

# Copy dependancies
COPY /base/requirements.txt ${LAMBDA_TASK_ROOT}

# Copy invoke functions
COPY faas_specific/faasr_start_invoke_aws.py ${LAMBDA_TASK_ROOT}

RUN dnf install -y R git

# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is tha name of the user's GitHub repository to install FaaSr from e.g. janedoe/faasr-py-dev
ARG FAASR_INSTALL_REPO

# Download dependancies
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install "${FAASR_INSTALL_REPO}@${FAASR_VERSION}"

# Run invoke script
CMD ["faasr_start_invoke_aws.handler"]
