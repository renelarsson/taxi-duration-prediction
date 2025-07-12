# Capstone Project Plan

## 1. Project Overview
- **Problem:** Predict NYC taxi ride durations in real-time for incoming ride events.
- **Objectives:** Build a robust, production-ready MLOps pipeline for model training, deployment, monitoring, and automation.
- **Expected Outcomes:** Automated data ingestion, model training, deployment to AWS Lambda, real-time predictions via Kinesis, and continuous monitoring.

## 2. Data Pipeline
- **Sources:** NYC taxi trip data (parquet files) downloaded via scripts in `src/data/extract.py`.
- **Ingestion:** Automated download and storage in the `data/` directory.
- **Preprocessing:** Cleaning, duration calculation, filtering, and feature engineering in `src/data/preprocess.py`.
- **Features:** Categorical (PU_DO, PULocationID, DOLocationID) and numerical (trip_distance).

## 3. Model Development
- **Models:** RandomForestRegressor, LinearRegression, XGBoost (see `src/models/train.py` and `workflows/training_pipeline.py`).
- **Training:** Split data into train/validation, use DictVectorizer for feature encoding.
- **Evaluation:** RMSE and MAE metrics; tracked in MLflow.

## 4. Experiment Tracking
- **Tool:** MLflow for experiment tracking, artifact logging, and model registry.
- **Logging:** Parameters, metrics, and artifacts are logged during training.
- **Comparison:** Experiments tracked and compared via MLflow UI and database.

## 5. Model Deployment
- **Strategy:** Containerized model deployed to AWS Lambda using Docker (`Dockerfile`), triggered by Kinesis events.
- **Infrastructure:** Managed via Terraform modules (`infrastructure/terraform/modules/`).
- **CI/CD:** Automated with GitHub Actions workflows (`.github/workflows/ci.yaml`, `.github/workflows/cd.yaml`).

## 6. Monitoring & Observability
- **Performance:** Evidently used for drift detection and metrics calculation (`src/monitoring/evidently_monitor.py`).
- **Data Drift:** Reference and current data compared, metrics stored in PostgreSQL.
- **Logging:** Lambda logs monitored in AWS CloudWatch; dashboards can be set up in Grafana.

## 7. Testing
- **Unit Tests:** Core logic tested in `tests/unit/model_test.py`.
- **Integration Tests:** End-to-end pipeline and workflow tests in `tests/integration/` and `integration-test/`.
- **E2E Tests:** Automated cloud tests in `scripts/test_cloud_e2e.sh`.

## 8. Project Structure & Configuration
- **Environment Variables:**
  - All configuration (AWS, MLflow, database, streaming) is managed via environment variables in `.env.example`.
  - Update `.env.example` with your own secrets and settings before running the project.
- **Directories:**
  - `src/`: Source code (data, models, deployment, monitoring)
  - `infrastructure/`: Terraform modules and configs
  - `tests/`: Unit and integration tests
  - `integration-test/`: Docker-based integration tests and model artifacts
  - `scripts/`: Automation scripts for deployment, publishing, and testing
  - `.github/workflows/`: CI/CD pipelines
  - `.vscode/`: Editor settings
- **Key Scripts:**
  - `deploy_manual.sh`: Manual deployment
  - `publish.sh`: Docker image publishing
  - `test_cloud_e2e.sh`: Cloud E2E testing
  - `run.sh`: Integration test runner

## 9. Future Improvements
- Add automated retraining and model selection workflows.
- Enhance monitoring with alerting and Grafana dashboards.
- Expand test coverage and add more E2E scenarios.
- Optimize model hyperparameters and experiment tracking.
- Add support for multiple model versions and rollback.

## 10. References
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Prefect Documentation](https://docs.prefect.io/)
- [Evidently Documentation](https://docs.evidentlyai.com/)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Terraform](https://www.terraform.io/docs/)