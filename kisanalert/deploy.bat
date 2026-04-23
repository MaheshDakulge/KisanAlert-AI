@echo off
echo =======================================================
echo KisanAlert v2.0 - Google Cloud Run Initializer
echo =======================================================
echo.
echo Make sure you have installed Google Cloud CLI.
echo If this is your first time, remember to run:
echo   1. gcloud auth login
echo.
set /p PROJECT_ID="Enter your Google Cloud Project ID (e.g. kisan-alert-12345): "
echo Setting active project to %PROJECT_ID%...
call gcloud config set project %PROJECT_ID%
echo.

echo Deploying FastAPI Backend to Cloud Run...
call gcloud run deploy kisanalert-api ^
  --source . ^
  --region asia-south1 ^
  --allow-unauthenticated ^
  --port 8080 ^
  --memory 2Gi ^
  --update-env-vars="GEMINI_API_KEY=AIzaSyALAy1jABCIwABNGKhMewA6zMIc93EajJQ,SUPABASE_URL=https://hhifndxlnbgnfnogjize.supabase.co,SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhoaWZuZHhsbmJnbmZub2dqaXplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxODU0NzYsImV4cCI6MjA5MTc2MTQ3Nn0.6zfmcFh5xqDSFC7Bgb19zpe2GX1AQu3vph_xTtVtMkM,SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhoaWZuZHhsbmJnbmZub2dqaXplIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjE4NTQ3NiwiZXhwIjoyMDkxNzYxNDc2fQ.dqRSCfe2baNTEkRP1PK9XKbcqixI62jyPoj4cDjmkHg,DATAGOV_API_KEY=579b464db66ec23bdd000001d6fc08f66c5a42634da6bd8cb5237a22,TINYFISH_API_KEY=sk-tinyfish-1trMNE1UOXOB58ePDnK9-jXZKokZmLwy"

echo.
echo =======================================================
echo Deployment Command Finished!
echo If successful, copy the Service URL (https://kisanalert-api-...)
echo and paste it into your Twilio Sandbox Webhook!
echo =======================================================
pause
