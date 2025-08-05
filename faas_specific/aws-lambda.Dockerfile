FROM public.ecr.aws/lambda/python:3.13

# Copy dependancies
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Copy invoke functions
COPY faasr_start_invoke_aws.py ${LAMBDA_TASK_ROOT}

# Download dependancies
RUN pip install --no-cache-dir -r requirements.txt

# Run invoke script
CMD ["faasr_start_invoke_aws.handler"]
