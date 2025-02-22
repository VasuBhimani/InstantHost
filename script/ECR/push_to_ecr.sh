#!/bin/bash

AWS_REGION="us-west-2"

# Get ECR URL from Terraform output
ECR_URL=$(terraform output -raw ecr_repository_url)

# Accept IMAGE_NAME and IMAGE_TAG as command-line arguments or use defaults
IMAGE_NAME=${1:-"my-default-image"}
IMAGE_TAG=${2:-"latest"}

echo "Using IMAGE_NAME: $IMAGE_NAME"
echo "Using IMAGE_TAG: $IMAGE_TAG"

# Authenticate with ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

# Tag and push the existing image
echo "Tagging existing Docker image..."
docker tag $IMAGE_NAME:latest $ECR_URL:$IMAGE_TAG

echo "Pushing Docker image to AWS ECR..."
docker push $ECR_URL:$IMAGE_TAG

# Force ECS service to update with the new image
CLUSTER_NAME="my-ecs-cluster"
SERVICE_NAME="my-service"

aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment

echo "ECS service updated with new image!"
