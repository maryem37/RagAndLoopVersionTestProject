[CmdletBinding()]
param(
  [string]$AuthBaseUrl  = 'http://127.0.0.1:9000',
  [string]$LeaveBaseUrl = 'http://127.0.0.1:9001',
  [string]$Email,
  [string]$Password,
  [string]$JWT
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

# ----------------------------
# BALANCE CHECK
# ----------------------------
$getUrl = "$LeaveBaseUrl/api/balances/$uid"
$get    = Invoke-Http -Method GET -Url $getUrl -Headers $headers

if ($get.StatusCode -eq 200) {
  Write-Host ("[OK] Balance found for userId={0}" -f $uid) -ForegroundColor Green
  Write-Host $get.Content
}
else {
  Write-Host ("[WARN] No balance found (HTTP {0})" -f $get.StatusCode) -ForegroundColor Yellow
}