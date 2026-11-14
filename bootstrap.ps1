# Windows PowerShell 5.1 or PowerShell 7.
[CmdletBinding()]
param(
    [ValidateSet('check','setup','verify','connect','disconnect','ssh','sftp','mosh','route')][string]$Action='check',
    [string]$Bundle,
    [string]$Sha256,
    [string]$StateRoot,
    [string]$Endpoint,
    [switch]$InstallClients,
    [switch]$NoActivate
)
& (Join-Path $PSScriptRoot 'scripts/windows.ps1') @PSBoundParameters
exit $LASTEXITCODE
