' VBScript to run the batch file silently
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\weiss\Desktop\JT101\OS\open_google_doc.bat""", 0, False