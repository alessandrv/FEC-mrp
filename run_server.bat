@echo off
echo Starting MRP Combined Application...
echo This will run both backend.py (port 8000) and backend_availability.py (port 8001) in the same process
cd /d %~dp0
C:\Users\Fecadm\AppData\Local\Programs\Python\Python312-32\python.exe main.py
pause 