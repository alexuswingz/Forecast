param(
    [string]$SqlitePath = "kpi_metrics.db",
    [string]$RdsHost = "your-instance.abc123xyz.us-east-1.rds.amazonaws.com",
    [int]$RdsPort = 5432,
    [string]$Database = "kpi_metrics",
    [string]$DbUser = "postgres",
    [string]$DbPassword = ""
)

if (-not (Get-Command pgloader -ErrorAction SilentlyContinue)) {
    Write-Error "pgloader is not installed or not on PATH. Install it (e.g., via WSL or Docker) before running this script."
    exit 1
}

if (-not (Test-Path $SqlitePath)) {
    Write-Error "SQLite file '$SqlitePath' not found."
    exit 1
}

if ([string]::IsNullOrEmpty($DbPassword)) {
    $DbPassword = Read-Host -Prompt "Enter RDS PostgreSQL password" -AsSecureString | `
        ForEach-Object { [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) }
}

$pgConnection = "postgresql://$DbUser:`"$DbPassword`"@$RdsHost:$RdsPort/$Database"
Write-Host "Running pgloader ..."
Write-Host "Source : $SqlitePath"
Write-Host "Target : $pgConnection"

$env:PGPASSWORD = $DbPassword
pgloader $SqlitePath $pgConnection
if ($LASTEXITCODE -eq 0) {
    Write-Host "Migration completed successfully."
} else {
    Write-Error "pgloader exited with code $LASTEXITCODE"
}

