param([ValidateSet('writer', 'consumer')][string]$Stage = 'writer')
$ErrorActionPreference = 'Stop'
$trialRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
# Python preserves the native CLI's TOML quoting on Windows PowerShell 5.
& py -3.11 (Join-Path $PSScriptRoot 'session.py') $Stage
exit $LASTEXITCODE
