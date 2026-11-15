# Atualiza o dash do perfil: busca os números, regera os SVGs e publica se mudou.
# Roda todo dia pela tarefa "Perfil GitHub - dash" do Agendador do Windows.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$log = Join-Path $PSScriptRoot 'atualizar.log'
try {
    git pull -q --rebase origin main 2>$null
    python (Join-Path $PSScriptRoot 'gerar.py') | Out-Null
    git add dash/escuro.svg dash/claro.svg
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -q -m "Atualiza o dash"
        git push -q origin main 2>$null
    }
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm') ok" | Out-File $log -Append -Encoding utf8
} catch {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm') erro: $($_.Exception.Message)" | Out-File $log -Append -Encoding utf8
}
