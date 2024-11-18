@echo off
pushd ..\..\chatbot-backend\venv\Scripts
call activate  # Activate virtual environment
popd
pushd ..\..\chatbot-backend
call python main.py  # Start backend
popd
pause
