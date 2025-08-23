# BASE_IMAGE is the full name of the base image e.g. public.ecr.aws/lambda/python:3.13
ARG BASE_IMAGE
# Start from specified base image
FROM $BASE_IMAGE

# Set environment variable for platform
ENV FAASR_PLATFORM="lambda"

# Set working dir to ${LAMBDA_TASK_ROOT}
WORKDIR /var/task

COPY faasr_entry.py ./

# FAASR_VERSION FaaSr version to install from - this must match a tag in the GitHub repository e.g. 1.1.2
ARG FAASR_VERSION
# FAASR_INSTALL_REPO is tha name of the user's GitHub repository to install FaaSr from e.g. janedoe/faasr-py-dev
ARG FAASR_INSTALL_REPO

RUN pip install --no-cache-dir awslambdaric \
 && pip install --no-cache-dir "git+https://github.com/${FAASR_INSTALL_REPO}.git@${FAASR_VERSION}"

ENTRYPOINT ["python", "-m", "awslambdaric"]

# Run invoke script
CMD ["faasr_entry.handler"]
