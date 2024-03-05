@echo off
start /MIN cmd /c "call C:\Users\christian\Desktop\Brgy\env\Scripts\activate && python manage.py runserver > server.log 2>&1"
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000/