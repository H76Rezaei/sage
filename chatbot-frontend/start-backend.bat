@echo off
pushd ..\..\sage\venv\Scripts
call activate  # Activate virtual environment
popd
pushd ..\..\sage
call python main.py  # Start backend
popd
pause
