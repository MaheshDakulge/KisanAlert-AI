@echo off
:: ============================================
:: KisanAlert Daily Automation Script
:: This runs the ML pipeline and pushes to Supabase
:: ============================================

:: Force UTF-8 encoding for command prompt
chcp 65001 >nul

:: Change to the project directory
cd /d "c:\FlutterDev\projects\Agri\kisanalert"

:: Log the execution time
echo [%date% %time%] Running KisanAlert Daily Pipeline... >> logs\automation.log

:: Execute the pipeline
python run_pipeline.py >> logs\automation.log 2>&1

:: Check if the pipeline succeeded
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] SUCCESS >> logs\automation.log
) else (
    echo [%date% %time%] ERROR: Pipeline failed. Check pipeline.log for details. >> logs\automation.log
)

echo -------------------------------------------------- >> logs\automation.log
exit
