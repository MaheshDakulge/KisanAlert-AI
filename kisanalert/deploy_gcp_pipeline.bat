@echo off
echo =================================================================
echo KisanAlert - Scheduled ML Pipeline Deployment
echo Architecture: Cloud Run Job + Cloud Scheduler
echo =================================================================
echo.

set GCP_REGION=asia-south1
set PROJECT_ID=reliable-signal-zg0gn

echo Step 1: Deploying the ML Pipeline as a Google Cloud Run Job...
echo Once deployed, this job only costs money when it actually runs.
echo.
gcloud run jobs deploy kisanalert-pipeline ^
  --source . ^
  --region %GCP_REGION% ^
  --max-retries 1 ^
  --task-timeout 10m ^
  --command "python" ^
  --args "run_pipeline.py,--crop,Soybean" ^
  --set-env-vars="GEMINI_API_KEY=YOUR_KEY_HERE,SUPABASE_URL=YOUR_URL_HERE,SUPABASE_KEY=YOUR_KEY_HERE"

echo.
echo Step 2: Setting up Google Cloud Scheduler...
echo Scheduling the pipeline to run twice a day (11 AM and 6 PM IST).
echo This ensures farmers get the freshest predictions right after market hours.
echo.

:: 08:00 AM IST Schedule (02:30 UTC)
gcloud scheduler jobs create http trigger-kisanalert-morning ^
  --schedule="30 2 * * *" ^
  --time-zone="UTC" ^
  --uri="https://%GCP_REGION%-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/%PROJECT_ID%/jobs/kisanalert-pipeline:run" ^
  --http-method="POST" ^
  --oauth-service-account-email="5607697238-compute@developer.gserviceaccount.com"

:: 6:00 PM IST Schedule (18:00 IST = 12:30 UTC)
gcloud scheduler jobs create http trigger-kisanalert-evening ^
  --schedule="30 12 * * *" ^
  --time-zone="UTC" ^
  --uri="https://%GCP_REGION%-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/%PROJECT_ID%/jobs/kisanalert-pipeline:run" ^
  --http-method="POST" ^
  --oauth-service-account-email="5607697238-compute@developer.gserviceaccount.com"

echo.
echo =================================================================
echo Setup Complete! 
echo 1. The API endpoint handles mobile app requests 24/7.
echo 2. The Cloud Scheduler triggers the heavy ML job at 11 AM and 6 PM daily.
echo =================================================================
pause
