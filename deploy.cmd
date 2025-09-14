@echo off

echo Starting deployment...

REM Install Python dependencies
echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Deployment completed successfully!
