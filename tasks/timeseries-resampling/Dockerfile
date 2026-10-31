# Reproducible environment for the "timeseries-resampling" task.
#
# The harness mounts the run's scratch copy of environment/ over /workspace, so
# the COPY below is what makes the image usable on its own:
#
#   docker build -t stbench/timeseries-resampling tasks/timeseries-resampling
#   docker run --rm -it stbench/timeseries-resampling
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

# Pinned so a run in 2027 sees the same numerics as a run today.
RUN pip install --no-cache-dir "numpy==2.1.3" "pytest==8.3.4"

WORKDIR /workspace
COPY environment/ /workspace/

CMD ["bash"]
