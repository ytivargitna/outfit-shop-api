#!/usr/bin/env bash
set -e

GITLAB_TOKEN="glpat-vC5N7UZ6oJMhVlqtw_Zv4WM6MQpvOjEKdTpkbms4cQ8.01.170nvgebu"
PROJECT_NAME="outfit-shop-api"
GITLAB_USER="shiliaiwei"

echo "1. Creating project '${PROJECT_NAME}' on GitLab for user '${GITLAB_USER}'..."
CREATE_RESP=$(curl -s --request POST "https://gitlab.com/api/v4/projects" \
     --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
     --data "name=${PROJECT_NAME}&visibility=private")

echo "GitLab API Response:"
echo "$CREATE_RESP" | grep -o '"web_url":"[^"]*"' || echo "Project creation processed or already exists."

echo ""
echo "2. Pushing all branches (docs, main, main-product) and resources to GitLab..."
git push gitlab --all

echo ""
echo "Deployment to GitLab complete!"
