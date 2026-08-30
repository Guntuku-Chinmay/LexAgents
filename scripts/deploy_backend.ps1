# deploy_backend.ps1
# Build, local test, and push LexAgents Backend to AWS ECR

$ErrorActionPreference = "Stop"

$ECR_REGISTRY = "579869950897.dkr.ecr.ap-south-1.amazonaws.com"
$REPO_NAME = "lexagents-backend"
$REGION = "ap-south-1"
$IMAGE_TAG = "latest"
$FULL_ECR_PATH = "$ECR_REGISTRY/$REPO_NAME:$IMAGE_TAG"
$LOCAL_IMAGE = "lexagents-backend:latest"
$TEST_PORT = 8000

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "1. Testing local AWS configuration..." -ForegroundColor Cyan
try {
    $identity = aws sts get-caller-identity
    Write-Host "Authenticated as: $identity" -ForegroundColor Green
} catch {
    Write-Error "AWS CLI is not configured or lacks credentials. Run 'aws configure' first."
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "2. Building Docker image..." -ForegroundColor Cyan
docker build -f backend/Dockerfile -t $LOCAL_IMAGE .
Write-Host "Docker build completed successfully." -ForegroundColor Green

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "3. Running container locally for validation..." -ForegroundColor Cyan
# Clean up existing test container if present
try {
    docker stop lexagents-backend-test -ErrorAction SilentlyContinue | Out-Null
    docker rm lexagents-backend-test -ErrorAction SilentlyContinue | Out-Null
} catch {}

$containerId = docker run -d --name lexagents-backend-test -p "$($TEST_PORT):8000" -e PORT=8000 $LOCAL_IMAGE
Write-Host "Container started with ID: $containerId"

Write-Host "Waiting 5 seconds for application startup..."
Start-Sleep -Seconds 5

Write-Host "Checking health check endpoint at http://localhost:$TEST_PORT/health..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:$TEST_PORT/health" -Method Get
    Write-Host "Health Check Success! Response:" -ForegroundColor Green
    $response | ConvertTo-Json | Write-Host
} catch {
    docker logs lexagents-backend-test
    docker stop lexagents-backend-test | Out-Null
    docker rm lexagents-backend-test | Out-Null
    Write-Error "Health check failed. The container logs are printed above."
}

# Stop and remove the test container
Write-Host "Stopping and cleaning up local test container..."
docker stop lexagents-backend-test | Out-Null
docker rm lexagents-backend-test | Out-Null
Write-Host "Local verification completed successfully." -ForegroundColor Green

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "4. Authenticating Docker with Amazon ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "5. Tagging image for ECR..." -ForegroundColor Cyan
docker tag $LOCAL_IMAGE $FULL_ECR_PATH
Write-Host "Tagged image as: $FULL_ECR_PATH" -ForegroundColor Green

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "6. Pushing image to Amazon ECR..." -ForegroundColor Cyan
docker push $FULL_ECR_PATH
Write-Host "Image successfully pushed to ECR." -ForegroundColor Green

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "7. Verifying pushed image details..." -ForegroundColor Cyan
aws ecr describe-images --repository-name $REPO_NAME --image-ids imageTag=$IMAGE_TAG
Write-Host "All steps completed successfully!" -ForegroundColor Green
