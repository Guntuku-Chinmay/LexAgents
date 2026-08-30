#!/usr/bin/env bash
# Build, local test, and push LexAgents Backend to AWS ECR

set -e

ECR_REGISTRY="579869950897.dkr.ecr.ap-south-1.amazonaws.com"
REPO_NAME="lexagents-backend"
REGION="ap-south-1"
IMAGE_TAG="latest"
FULL_ECR_PATH="$ECR_REGISTRY/$REPO_NAME:$IMAGE_TAG"
LOCAL_IMAGE="lexagents-backend:latest"
TEST_PORT=8000

echo "=============================================="
echo "1. Testing local AWS configuration..."
if ! identity=$(aws sts get-caller-identity); then
    echo "Error: AWS CLI is not configured or lacks credentials. Run 'aws configure' first." >&2
    exit 1
fi
echo "Authenticated as: $identity"

echo "=============================================="
echo "2. Building Docker image..."
docker build -f backend/Dockerfile -t "$LOCAL_IMAGE" .
echo "Docker build completed successfully."

echo "=============================================="
echo "3. Running container locally for validation..."
# Clean up existing test container if present
docker stop lexagents-backend-test >/dev/null 2>&1 || true
docker rm lexagents-backend-test >/dev/null 2>&1 || true

containerId=$(docker run -d --name lexagents-backend-test -p "${TEST_PORT}:8000" -e PORT=8000 "$LOCAL_IMAGE")
echo "Container started with ID: $containerId"

echo "Waiting 5 seconds for application startup..."
sleep 5

echo "Checking health check endpoint at http://localhost:$TEST_PORT/health..."
if response=$(curl -sS --fail "http://localhost:$TEST_PORT/health"); then
    echo "Health Check Success! Response:"
    echo "$response"
else
    echo "Error: Health check failed. Printing container logs..." >&2
    docker logs lexagents-backend-test
    docker stop lexagents-backend-test >/dev/null 2>&1 || true
    docker rm lexagents-backend-test >/dev/null 2>&1 || true
    exit 1
fi

# Stop and remove the test container
echo "Stopping and cleaning up local test container..."
docker stop lexagents-backend-test >/dev/null 2>&1 || true
docker rm lexagents-backend-test >/dev/null 2>&1 || true
echo "Local verification completed successfully."

echo "=============================================="
echo "4. Authenticating Docker with Amazon ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "=============================================="
echo "5. Tagging image for ECR..."
docker tag "$LOCAL_IMAGE" "$FULL_ECR_PATH"
echo "Tagged image as: $FULL_ECR_PATH"

echo "=============================================="
echo "6. Pushing image to Amazon ECR..."
docker push "$FULL_ECR_PATH"
echo "Image successfully pushed to ECR."

echo "=============================================="
echo "7. Verifying pushed image details..."
aws ecr describe-images --repository-name "$REPO_NAME" --image-ids imageTag="$IMAGE_TAG"
echo "All steps completed successfully!"
