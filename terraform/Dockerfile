# Dockerfile for AWS Lambda Python 3.9
# This Dockerfile sets up a Lambda function environment with Python 3.9
# and installs the necessary dependencies from requirements.txt.

FROM public.ecr.aws/lambda/python:3.9

RUN pip install -U pip
RUN pip install pytest

# Copy requirements.txt from terraform/ and install dependencies into Lambda task root
COPY terraform/requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy directories into the Lambda task root
COPY terraform/ ${LAMBDA_TASK_ROOT}/terraform/
# Remove for SAM/deployment
COPY src/ ${LAMBDA_TASK_ROOT}/src/ 
# Remove for SAM/deployment
COPY .env.dev ${LAMBDA_TASK_ROOT}/.env.dev 
COPY .env.prod ${LAMBDA_TASK_ROOT}/.env.prod
# Remove for SAM/deployment
COPY tests/ ${LAMBDA_TASK_ROOT}/tests/ 
# Remove for SAM/deployment
COPY tests/integration/ ${LAMBDA_TASK_ROOT}/tests/integration/ 

# Set PYTHONPATH so Python can find the src package
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

WORKDIR /app

# Set the handler
CMD ["terraform/lambda_function.lambda_handler"]