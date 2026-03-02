#!/bin/bash
# =============================================================================
# DSE Cal-Adapt Pipeline — Docker Runner
# =============================================================================
#
# Usage:
#   ./docker/run_docker.sh build      # Build the image
#   ./docker/run_docker.sh notebook   # Start JupyterLab on port 8888
#   ./docker/run_docker.sh pipeline   # Run headless full extraction
#   ./docker/run_docker.sh shell      # Interactive bash shell
#
# Prerequisites:
#   - Docker installed
#
# First-time Coiled setup:
#   ./docker/run_docker.sh shell
#   coiled login                  # copy the URL it prints into your browser
#   exit
#
# =============================================================================

set -e

IMAGE_NAME="dse/caladapt-pipeline"
CONTAINER_NAME="dse_pipeline"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Coiled credentials location on host
COILED_CONFIG="$HOME/.config/dask"

# Common docker run args:
#   - Mount data/ for persistent output
#   - Mount coiled/dask config for auth
#   - Mount notebooks/ so edits persist on host
DOCKER_RUN_ARGS=(
    --name "$CONTAINER_NAME"
    --rm
    -v "$PROJECT_ROOT/data:/pipeline/data"
    -v "$PROJECT_ROOT/notebooks:/pipeline/notebooks"
    -v "$PROJECT_ROOT/lib:/pipeline/lib"
)

# Mount Coiled credentials (create dir if first time so coiled login works from inside container)
mkdir -p "$COILED_CONFIG"
DOCKER_RUN_ARGS+=(-v "$COILED_CONFIG:/root/.config/dask")

# Pass GCP credentials if set
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    DOCKER_RUN_ARGS+=(
        -v "$GOOGLE_APPLICATION_CREDENTIALS:/tmp/gcp-key.json:ro"
        -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json
    )
fi

case "${1:-notebook}" in
    build)
        echo "Building image: $IMAGE_NAME"
        docker build -t "$IMAGE_NAME" "$PROJECT_ROOT"
        echo "Done. Image: $IMAGE_NAME"
        ;;

    notebook)
        echo "Starting JupyterLab..."
        echo "  Open: http://localhost:8888"
        echo "  Press Ctrl+C to stop"
        docker run -it \
            "${DOCKER_RUN_ARGS[@]}" \
            -p 8888:8888 \
            "$IMAGE_NAME" notebook
        ;;

    pipeline)
        echo "Running full extraction pipeline..."
        docker run -it \
            "${DOCKER_RUN_ARGS[@]}" \
            "$IMAGE_NAME" pipeline "${@:2}"
        ;;

    shell)
        echo "Starting interactive shell..."
        docker run -it \
            "${DOCKER_RUN_ARGS[@]}" \
            "$IMAGE_NAME" shell
        ;;

    *)
        echo "Usage: $0 {build|notebook|pipeline|shell}"
        echo ""
        echo "  build     Build the Docker image"
        echo "  notebook  Start JupyterLab on port 8888"
        echo "  pipeline  Run headless full data extraction"
        echo "  shell     Interactive bash shell"
        exit 1
        ;;
esac
