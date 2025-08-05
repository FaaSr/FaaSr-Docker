FROM public.ecr.aws/lambda/python:latest

# Copy dependancies
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Copy invoke functions
COPY faasr_start_invoke_aws.py ${LAMBDA_TASK_ROOT}

#Install R 
RUN dnf install -y R
RUN Rscript -e "install.packages(c('jsonlite', 'httr'), repos='https://cloud.r-project.org')"

# Download dependancies
RUN pip install --no-cache-dir -r requirements.txt

# Run invoke script
CMD ["faasr_start_invoke_aws.handler"]
