' VBScript to run the batch file silently
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Users\JellyTracker\Desktop\JellyFishTrackingPC-main\OS\open_google_doc.bat""", 0, False