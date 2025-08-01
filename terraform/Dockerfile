FROM public.ecr.aws/lambda/python:3.9

# Install pip and pytest
RUN pip install -U pip
RUN pip install pytest

# Copy requirements and install dependencies
COPY terraform/requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy application code
COPY terraform/ ${LAMBDA_TASK_ROOT}/terraform/
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Create empty environment files for CI/CD (no COPY needed)
RUN touch ${LAMBDA_TASK_ROOT}/.env.dev ${LAMBDA_TASK_ROOT}/.env.prod

# Copy tests
COPY tests/ ${LAMBDA_TASK_ROOT}/tests/
COPY tests/integration/ ${LAMBDA_TASK_ROOT}/tests/integration/
COPY tests/integration/event.json ${LAMBDA_TASK_ROOT}/tests/integration/event.json

WORKDIR /app

CMD ["terraform.lambda_function.lambda_handler"]