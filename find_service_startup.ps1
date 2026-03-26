# Restart Services with JaCoCo Coverage Monitoring
# Run this script after finding where the services are running

# First, let's find Java processes and their JAR files
Write-Host "Finding running Java services..."
$javaPids = @()
$javaProcs = Get-Process java -ErrorAction SilentlyContinue

foreach ($proc in $javaProcs) {
    $pid = $proc.Id
    $cmdline = (Get-WmiObject Win32_Process | Where-Object ProcessId -eq $pid).CommandLine
    if ($cmdline) {
        Write-Host "PID: $pid"
        Write-Host "Command: $cmdline"
        Write-Host ""
    }
}

# Try to find JAR files in common locations
Write-Host "`nSearching for JAR files in common locations..."
$jarSearchPaths = @(
    "C:\",
    "C:\Bureau",
    "C:\Bureau\Bureau",
    "C:\Program Files",
    "C:\Users\*\Downloads"
)

foreach ($path in $jarSearchPaths) {
    $jars = @(Get-ChildItem -Path $path -Filter "*.jar" -ErrorAction SilentlyContinue -Recurse | Select-Object -First 5)
    if ($jars.Count -gt 0) {
        Write-Host "`nFound in $path :"
        foreach ($jar in $jars) {
            Write-Host "  - $($jar.FullName)"
        }
    }
}

# Check listening ports
Write-Host "`n`nServices listening on ports 9000 and 9001:"
netstat -ano | Select-String "9000|9001" | ForEach-Object {
    Write-Host $_
}
