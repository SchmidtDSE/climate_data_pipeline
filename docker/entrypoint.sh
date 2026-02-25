#!/bin/bash
# =============================================================================
# Container entrypoint — activates conda env and dispatches command
# =============================================================================

# Activate conda
eval "$(conda shell.bash hook)"
conda activate py-env

case "${1:-notebook}" in
    notebook)
        echo "Starting JupyterLab..."
        exec jupyter lab \
            --ip=0.0.0.0 \
            --port=8888 \
            --no-browser \
            --allow-root \
            --notebook-dir=/pipeline/notebooks
        ;;

    pipeline)
        echo "Running extraction pipeline..."
        exec python /pipeline/docker/run_pipeline.py "${@:2}"
        ;;

    shell)
        exec /bin/bash
        ;;

    *)
        exec "$@"
        ;;
esac
