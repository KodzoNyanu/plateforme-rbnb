# =============================================================================
#  Configuration du PostgreSQL natif pour le projet Rbnb
#  À LANCER EN ADMINISTRATEUR — usage unique.
#
#  Contexte : le port 5432 est occupé par un conteneur Docker (autre projet).
#  Ce script fait donc tourner le PostgreSQL natif sur le port 5433, et :
#    1. règle le port sur 5433 (postgresql.conf),
#    2. bascule temporairement l'authentification en "trust",
#    3. démarre PostgreSQL,
#    4. définit un nouveau mot de passe pour l'utilisateur "postgres",
#    5. RESTAURE l'authentification sécurisée + redémarre,
#    6. écrit le mot de passe ET le port 5433 dans le fichier .env du projet.
#
#  La sécurité est toujours remise en place, même en cas d'erreur (bloc finally).
# =============================================================================
$ErrorActionPreference = "Stop"

$pgDir   = "C:\Program Files\PostgreSQL\16"
$conf    = Join-Path $pgDir "data\postgresql.conf"
$hba     = Join-Path $pgDir "data\pg_hba.conf"
$psql    = Join-Path $pgDir "bin\psql.exe"
$service = "postgresql-x64-16"
$port    = 5433
$projet  = "D:\Projet Plateforme Rbnb"
$envFile = Join-Path $projet ".env"

# --- Vérifier les droits administrateur ---
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Host "STOP : lance ce script en ADMINISTRATEUR." -ForegroundColor Red
    exit 1
}

# --- Nouveau mot de passe alphanumérique (sûr dans une URL) ---
$newPass = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 20 | ForEach-Object {[char]$_})

# --- 1. Régler le port sur 5433 (append : la dernière valeur l'emporte) ---
if (-not (Select-String -Path $conf -Pattern "^\s*port\s*=\s*$port\b" -Quiet)) {
    Add-Content $conf "`n# --- Projet Rbnb : port dedie (evite le conflit avec Docker sur 5432) ---`nport = $port"
    Write-Host "-> Port regle sur $port dans postgresql.conf"
}

$backup = "$hba.bak_reset"
$ok = $false
try {
    Copy-Item $hba $backup -Force
    Write-Host "-> Bascule temporaire en authentification 'trust'..."
    (Get-Content $hba) -replace 'scram-sha-256', 'trust' | Set-Content $hba -Encoding ascii

    Write-Host "-> Demarrage de PostgreSQL sur le port $port..."
    if ((Get-Service $service).Status -eq 'Running') { Restart-Service $service } else { Start-Service $service }

    # Attendre que le serveur accepte les connexions (trust = sans mot de passe)
    $ready = $false
    for ($i = 0; $i -lt 15; $i++) {
        & $psql -U postgres -h 127.0.0.1 -p $port -d postgres -c "SELECT 1" *> $null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "PostgreSQL n'a pas demarre sur le port $port." }

    Write-Host "-> Definition du nouveau mot de passe..."
    & $psql -U postgres -h 127.0.0.1 -p $port -d postgres -c "ALTER USER postgres PASSWORD '$newPass';" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Echec de la commande ALTER USER." }
    $ok = $true
}
finally {
    Write-Host "-> Restauration de l'authentification securisee..."
    if (Test-Path $backup) { Copy-Item $backup $hba -Force; Remove-Item $backup -Force }
    Restart-Service $service
    Start-Sleep -Seconds 3
}

if ($ok) {
    if (Test-Path $envFile) {
        (Get-Content $envFile) -replace 'postgres:[^@]*@localhost:\d+', "postgres:$newPass@localhost:$port" |
            Set-Content $envFile -Encoding ascii
        Write-Host ""
        Write-Host "OK - PostgreSQL configure (port $port), mot de passe ecrit dans .env." -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "Nouveau mot de passe PostgreSQL : $newPass" -ForegroundColor Cyan
    Write-Host "(deja dans .env - garde-le pour toi, pas besoin de me l'envoyer.)"
} else {
    Write-Host "Echec : la securite a ete restauree. Rien n'a ete change cote mot de passe." -ForegroundColor Red
}
