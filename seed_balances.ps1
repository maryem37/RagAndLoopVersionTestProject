[CmdletBinding()]
param(
  [string]$AuthBaseUrl  = 'http://127.0.0.1:9000',
  [string]$LeaveBaseUrl = 'http://127.0.0.1:9001',
  [string]$Email,
  [string]$Password,
  [string]$JWT,
  [long[]]$UserIds,
  [double]$Annual,
  [double]$Recovery
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Http {
  param(
    [string]$Method,
    [string]$Url,
    [hashtable]$Headers,
    [object]$Body
  )

  try {
    if ($Body) {
      return Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers `
        -ContentType 'application/json' `
        -Body ($Body | ConvertTo-Json -Depth 10) `
        -UseBasicParsing -TimeoutSec 15
    }
    return Invoke-WebRequest -Method $Method -Uri $Url -Headers $Headers `
      -UseBasicParsing -TimeoutSec 15
  }
  catch {
    $resp = $_.Exception.Response
    if ($resp -and $resp.StatusCode) {
      $code = [int]$resp.StatusCode
      $text = ''
      try {
        $text = (New-Object IO.StreamReader($resp.GetResponseStream())).ReadToEnd()
      } catch {}
      return [pscustomobject]@{ StatusCode = $code; Content = $text; Error = $_.Exception.Message }
    }
    return [pscustomobject]@{ StatusCode = -1; Content = ''; Error = $_.Exception.Message }
  }
}

function Format-InvariantNumber {
  param([double]$Value)
  return $Value.ToString([System.Globalization.CultureInfo]::InvariantCulture)
}

Write-Host "AuthBaseUrl : $AuthBaseUrl"
Write-Host "LeaveBaseUrl: $LeaveBaseUrl"

# ----------------------------
# AUTH
# ----------------------------
if ($JWT) {
  $jwt = $JWT
  Write-Host "Using provided JWT."
}
elseif ($Email -and $Password) {
  $loginUrl = "$AuthBaseUrl/api/auth/login"
  Write-Host "Logging in: $loginUrl"

  $login = Invoke-RestMethod `
    -Uri $loginUrl `
    -Method Post `
    -ContentType 'application/json' `
    -Body (@{ email = $Email; password = $Password } | ConvertTo-Json) `
    -TimeoutSec 15

  if (-not $login.jwt) { throw "Login succeeded but JWT is missing" }

  $jwt = $login.jwt
  Write-Host "Login succeeded."
}
else {
  throw "Provide -JWT or -Email + -Password"
}

Write-Host "JWT acquired"

$headers = @{ Authorization = "Bearer $jwt" }
$shouldSeedValues = $PSBoundParameters.ContainsKey('Annual') -or $PSBoundParameters.ContainsKey('Recovery')

if ($shouldSeedValues -and (-not $PSBoundParameters.ContainsKey('Annual') -or -not $PSBoundParameters.ContainsKey('Recovery'))) {
  throw "When seeding explicit balances, provide both -Annual and -Recovery."
}

# ----------------------------
# USER DETECTION (SAFE)
# ----------------------------
$uid = 8   # fallback

$meUrl = "$AuthBaseUrl/api/users/me"
Write-Host "Fetching user info (optional)..."

$me = Invoke-Http -Method GET -Url $meUrl -Headers $headers

if ($me.StatusCode -eq 200) {
  try {
    $user = $me.Content | ConvertFrom-Json
    if ($user.id) {
      $uid  = $user.id
      Write-Host "Detected user: $($user.email) (id=$uid)"
    }
  }
  catch {
    Write-Host "[WARN] Could not parse /me response, using fallback userId=8"
  }
}
else {
  Write-Host ("[WARN] /me returned HTTP {0} -> using fallback userId=8" -f $me.StatusCode)
}

$targetUserIds = @()
if ($UserIds -and $UserIds.Count -gt 0) {
  $targetUserIds = @($UserIds)
}
else {
  $targetUserIds = @([long]$uid)
}

foreach ($targetUserId in $targetUserIds) {
  $getUrl = "$LeaveBaseUrl/api/balances/$targetUserId"
  $get    = Invoke-Http -Method GET -Url $getUrl -Headers $headers

  if (-not $shouldSeedValues) {
    if ($get.StatusCode -eq 200) {
      Write-Host ("[OK] Balance found for userId={0}" -f $targetUserId) -ForegroundColor Green
      Write-Host $get.Content
    }
    else {
      Write-Host ("[WARN] No balance found for userId={0} (HTTP {1})" -f $targetUserId, $get.StatusCode) -ForegroundColor Yellow
    }
    continue
  }

  if ($get.StatusCode -ne 200) {
    $initUrl = "$LeaveBaseUrl/api/balances/init/$targetUserId"
    Write-Host ("[INFO] Initializing balance for userId={0}..." -f $targetUserId)
    $init = Invoke-Http -Method POST -Url $initUrl -Headers $headers
    if ($init.StatusCode -lt 200 -or $init.StatusCode -ge 300) {
      throw ("Failed to initialize balance for userId={0}: HTTP {1} {2}" -f $targetUserId, $init.StatusCode, $init.Content)
    }
  }

  $annualText = Format-InvariantNumber -Value $Annual
  $recoveryText = Format-InvariantNumber -Value $Recovery
  $putUrl = "{0}/api/balances/{1}?annual={2}&recovery={3}" -f $LeaveBaseUrl, $targetUserId, $annualText, $recoveryText
  Write-Host ("[INFO] Seeding balance for userId={0} (annual={1}, recovery={2})..." -f $targetUserId, $annualText, $recoveryText)
  $put = Invoke-Http -Method PUT -Url $putUrl -Headers $headers

  if ($put.StatusCode -ge 200 -and $put.StatusCode -lt 300) {
    Write-Host ("[OK] Seeded balance for userId={0}" -f $targetUserId) -ForegroundColor Green
    Write-Host $put.Content
  }
  else {
    throw ("Failed to seed balance for userId={0}: HTTP {1} {2}" -f $targetUserId, $put.StatusCode, $put.Content)
  }
}
