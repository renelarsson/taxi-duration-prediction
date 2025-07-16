# Dockerfile for AWS Lambda Python 3.9
# This Dockerfile sets up a Lambda function environment with Python 3.9
# and installs the necessary dependencies from requirements.txt.
FROM public.ecr.aws/lambda/python:3.9

RUN pip install -U pip

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY lambda_function.py ./
COPY model.py ./

CMD [ "lambda_function.lambda_handler" ]