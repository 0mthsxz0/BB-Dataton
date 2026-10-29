$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $projectRoot '.env.local.json'
$settings = @{}
if (Test-Path -LiteralPath $configPath) {
    $saved = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    foreach ($item in $saved.PSObject.Properties) { $settings[$item.Name] = [string]$item.Value }
}

function Read-PrivateValue($label) {
    $secret = Read-Host $label -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

Write-Host 'Demonstracao local: cadastro por ID e chamadas com aprovacao na tela.'
Write-Host 'As configuracoes serao salvas neste computador, fora do Git.'
$settings['BB_DEMO_ID_LOOKUP'] = '1'
$settings['BB_VOICE_ENABLED'] = '1'
if (!$settings['PORT']) { $settings['PORT'] = '4183' }
if (!$settings['TWILIO_MODE']) { $settings['TWILIO_MODE'] = 'trial' }

foreach ($name in @('BB_INTERNAL_PASSWORD', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER')) {
    if (!$settings[$name]) {
        $inherited = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($inherited) { $settings[$name] = $inherited }
    }
}
while (!$settings['BB_INTERNAL_PASSWORD'] -or $settings['BB_INTERNAL_PASSWORD'].Length -lt 12) {
    $settings['BB_INTERNAL_PASSWORD'] = Read-PrivateValue 'Escolha a senha interna (minimo 12 caracteres)'
}
while ($settings['TWILIO_ACCOUNT_SID'] -notmatch '^AC[0-9a-fA-F]{32}$') {
    $settings['TWILIO_ACCOUNT_SID'] = (Read-Host 'Account SID da Twilio (iniciado por AC)').Trim()
}
while (!$settings['TWILIO_AUTH_TOKEN']) {
    $settings['TWILIO_AUTH_TOKEN'] = Read-PrivateValue 'Auth Token atual da Twilio'
}
if ($settings['TWILIO_MODE'] -eq 'completo') {
    while ($settings['TWILIO_FROM_NUMBER'] -notmatch '^\+[1-9]\d{7,14}$') {
        $settings['TWILIO_FROM_NUMBER'] = (Read-Host 'Numero de origem autorizado na Twilio (+ e codigo do pais)').Trim()
    }
}

if ($settings['TWILIO_MODE'] -eq 'trial') {
    $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Ambiente Python nao encontrado em .venv.' }
    if (!(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) {
        Start-Process -FilePath $pythonPath -ArgumentList 'servidor_voz.py' -WorkingDirectory $projectRoot -WindowStyle Hidden
    }
    try { $tunnels = Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 2 }
    catch { $tunnels = $null }
    if (!$tunnels) {
        $ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
        if ($ngrok) {
            Start-Process -FilePath $ngrok.Source -ArgumentList 'http', '8765' -WorkingDirectory $projectRoot -WindowStyle Hidden
            for ($attempt = 0; $attempt -lt 10; $attempt++) {
                Start-Sleep -Milliseconds 500
                try { $tunnels = Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 1; break } catch {}
            }
        }
    }
    $tunnel = $tunnels.tunnels | Where-Object { $_.public_url -like 'https://*' -and $_.config.addr -match '(^|:)8765/?$' } | Select-Object -First 1
    if ($tunnel) { $settings['TWILIO_TWIML_URL'] = $tunnel.public_url.TrimEnd('/') + '/voz.xml' }
    else { Write-Warning 'Inicie ngrok http 8765 e reabra este atalho para configurar o endereco de voz.' }
}

$settings | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
foreach ($key in $settings.Keys) { [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process') }
Write-Host 'Configuracao salva. Nao compartilhe o arquivo .env.local.json.'
if (Get-NetTCPConnection -LocalPort ([int]$settings['PORT']) -State Listen -ErrorAction SilentlyContinue) {
    Write-Host 'O site ja esta aberto. Pare o servidor antigo com Ctrl+C e execute este atalho novamente.'
    exit 1
}
Write-Host ('Abra http://localhost:' + $settings['PORT'] + '/interno')
& npm.cmd --prefix (Join-Path $projectRoot 'frontend') start
exit $LASTEXITCODE
