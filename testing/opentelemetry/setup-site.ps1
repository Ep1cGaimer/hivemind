param([switch]$Build)
$ErrorActionPreference = 'Stop'
$trialRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$repoPath = Join-Path $trialRoot '.local/opentelemetry.io'
function Run-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE" }
}
if (-not (Test-Path -LiteralPath (Join-Path $repoPath '.git'))) {
    throw 'Clone opentelemetry.io into .local/opentelemetry.io first.'
}
& git -c core.autocrlf=false -c core.longpaths=true -C $repoPath submodule update --init --depth 1
if ($LASTEXITCODE -ne 0) { throw 'Submodule initialization failed; inspect before retrying.' }
$containerNames = @(& docker ps -a --format '{{.Names}}')
if ($containerNames -contains 'otel-site-trial') {
    Run-Docker start otel-site-trial
} else {
    Run-Docker pull node:24.21.0-bookworm
    Run-Docker run -d --name otel-site-trial --restart unless-stopped `
      -p 127.0.0.1:1313:1313 `
      --mount "type=bind,source=$repoPath,target=/workspace" `
      --mount 'type=volume,source=otel-trial-node-modules,target=/workspace/node_modules' `
      -w /workspace node:24.21.0-bookworm sleep infinity
}
Run-Docker exec otel-site-trial git config --global --add safe.directory /workspace
Run-Docker exec otel-site-trial node --version
Run-Docker exec otel-site-trial npm --version
Run-Docker exec otel-site-trial npm run install:safe
if ($Build) { Run-Docker exec otel-site-trial npm run build }
