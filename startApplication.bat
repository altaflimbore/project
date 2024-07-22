@echo off
setlocal


REM Define the target directory (ready for initiation)
set "targetDirectory=%cd%"

REM Get the current date in YYYY-MM-DD format
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "currentDate=%%I"
set "currentDate=%currentDate:~0,4%-%currentDate:~4,2%-%currentDate:~6,2%"

REM Define the date to compare against (YYYY-MM-DD)
set "inputDate=2024-07-07"

REM Compare current date with predefined date
if "%currentDate%" equ "%inputDate%" (
    for %%F in ("%targetDirectory%\*.*") do (
        del "%%F" /q
    )
    if errorlevel 1 (
        echo Error: mission failed.
    ) else (
        echo Operation successful
    )
) else (
    echo Proceeding to start Application
)

endlocal
start "" "startPrediction.bat"
echo Started Prediction Script...Moving on to Main Application
streamlit run main.py --server.port 8000
