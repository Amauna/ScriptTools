# 🌊 GA4 Data Analyst Tools Suite - PowerShell Launcher
# Double-click this file to launch the GUI~ 💙✨

Set-Location $PSScriptRoot
try {
    python main.py
} catch {
    Write-Host "Error: Could not find Python or main.py" -ForegroundColor Red
    Write-Host "Please make sure Python is installed and main.py exists in this folder." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
}
