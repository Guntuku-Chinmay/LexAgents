# start-hackathon.ps1
# Automates checks and starts the LexAgents Docker Compose stack for the hackathon

$ErrorActionPreference = "Continue"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "     LexAgents Hackathon Startup Script       " -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Check Docker Desktop availability
Write-Host "Checking Docker Desktop service..." -ForegroundColor Yellow
$dockerCheck = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCheck) {
    Write-Host "Error: Docker CLI is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please download and install Docker Desktop first: https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    Pause
    exit 1
}

$dockerInfo = docker info -ErrorAction SilentlyContinue
if (-not $dockerInfo) {
    Write-Host "Error: Docker daemon is not running. Please start Docker Desktop." -ForegroundColor Red
    Pause
    exit 1
}
Write-Host "Docker daemon is active." -ForegroundColor Green

# 2. Check and prepare .env file
$envPath = Join-Path $PSScriptRoot ".env"
$envExamplePath = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path $envPath)) {
    Write-Host "Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item $envExamplePath $envPath
}

# Read existing env
$envLines = Get-Content $envPath -ErrorAction SilentlyContinue
$hasApiKey = $false
foreach ($line in $envLines) {
    if ($line -match "^OPENAI_API_KEY=(.+)") {
        $keyVal = $matches[1].Trim()
        if ($keyVal -ne "" -and $keyVal -ne "your-openai-api-key-here") {
            $hasApiKey = $true
        }
    }
}

if (-not $hasApiKey) {
    Write-Host ""
    Write-Host "----------------------------------------------" -ForegroundColor Yellow
    Write-Host "OPENAI_API_KEY is not configured in .env." -ForegroundColor Yellow
    Write-Host "The Multi-Agent legal planner requires an OpenAI API Key." -ForegroundColor Yellow
    Write-Host "----------------------------------------------" -ForegroundColor Yellow
    $userInputKey = Read-Host "Please enter your OpenAI API Key (or press Enter to skip and use test mock keys)"
    if ($userInputKey -ne "") {
        # Update/Append key
        $newLines = @()
        $found = $false
        foreach ($line in $envLines) {
            if ($line -match "^OPENAI_API_KEY=") {
                $newLines += "OPENAI_API_KEY=$userInputKey"
                $found = $true
            } else {
                $newLines += $line
            }
        }
        if (-not $found) {
            $newLines += "OPENAI_API_KEY=$userInputKey"
        }
        Set-Content -Path $envPath -Value $newLines
        Write-Host "Saved OpenAI API key to .env." -ForegroundColor Green
    }
}

# 3. Starting the stack
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Starting Docker Compose stack..." -ForegroundColor Yellow
Write-Host "Exposed endpoints:"
Write-Host " - Frontend UI:  http://localhost:3000" -ForegroundColor Green
Write-Host " - Backend API:  http://localhost:8000" -ForegroundColor Green
Write-Host " - Qdrant Panel: http://localhost:6333/dashboard" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan

docker compose down -v
docker compose up --build

Write-Host "Docker Compose stopped." -ForegroundColor Yellow
