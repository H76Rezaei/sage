@echo off

:: Navigate to chatbot-backend/venv/Scripts and activate virtual environment
pushd ..\..\sage\chatbot-backend\venv\Scripts
if exist activate.bat (
    call activate
    echo Virtual environment activated.
) else (
    echo Virtual environment not found. Please create it first.
    pause
    exit /b
)
popd

:: Navigate to chatbot-backend and run main.py
pushd ..\..\sage\chatbot-backend
if exist main.py (
    call python main.py
) else (
    echo main.py not found. Please ensure it exists in chatbot-backend.
    pause
    exit /b
)
popd

pause
