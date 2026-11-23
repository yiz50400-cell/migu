@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0.."
set "WORKFLOW_PYTHON=%CD%\runtime\python\python.exe"
if not exist "%WORKFLOW_PYTHON%" set "WORKFLOW_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%WORKFLOW_PYTHON%" (
  echo Python runtime missing. Follow README Windows source setup.
  exit /b 1
)
"%WORKFLOW_PYTHON%" -X utf8 scripts\check_windows_engine.py --require-windows
if errorlevel 1 exit /b %errorlevel%
if not exist "..\..\tests\test_install.py" (
  echo Migu release regression suite missing. Run this check inside the complete distribution.
  exit /b 1
)
pushd "..\.."
"%WORKFLOW_PYTHON%" -X utf8 -m unittest discover -s tests -v
set "REGRESSION_EXIT=%errorlevel%"
popd
exit /b %REGRESSION_EXIT%
