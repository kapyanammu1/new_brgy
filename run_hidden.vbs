Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -WindowStyle Hidden -Command ""Start-Process cmd -ArgumentList '/c BrgySystem.bat' -Verb RunAs""", 0, True