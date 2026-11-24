param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = "$ScriptDir;$env:PYTHONPATH"

$PythonBin = "python"
if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonBin = "$ScriptDir\.venv\Scripts\python.exe"
} elseif (Test-Path "$ScriptDir\..\.venv\Scripts\python.exe") {
    $PythonBin = "$ScriptDir\..\.venv\Scripts\python.exe"
}

& $PythonBin "$ScriptDir\main.py" @ArgsList
