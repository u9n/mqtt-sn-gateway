#!/bin/bash
set -euo pipefail

IMAGE_NAME=registry.u9n.dev/u9n/mqtt-sn-gateway

GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_COMMIT=$(git rev-parse --short HEAD)

# Pull previous version, and use with --cache-now
# for build caching:
docker pull $IMAGE_NAME:$GIT_BRANCH || true

# Use branch+commit for tagging:
docker build -t "$IMAGE_NAME:$GIT_BRANCH" \
             -t "$IMAGE_NAME:$GIT_COMMIT" \
             --build-arg BUILDKIT_INLINE_CACHE=1 \
             --cache-from=$IMAGE_NAME:$GIT_BRANCH .

# Security scanners:
#trivy image --ignore-unfixed --exit-code 1 \
#    $IMAGE_NAME:$GIT_BRANCH

# Push to the registry:
docker push "$IMAGE_NAME:$GIT_BRANCH"
docker push "$IMAGE_NAME:$GIT_COMMIT"