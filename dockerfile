FROM python:3.13.2 
# Copy uv binary from official uv image (multi-stage build pattern) 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/ 
 
WORKDIR /app 
 
ENV PATH="/app/.venv/bin:$PATH" 
 
# Copy dependency files first (better layer caching) 
COPY "pyproject.toml" "uv.lock" ".python-version" ./ 
# Install dependencies from lock file (ensures reproducible builds) 
RUN uv sync --locked  --no-install-project       
#--no-install-project flag is used to install only the dependencies specified in the lock file, without installing the project itself. 
 
# Copy application code 
COPY pipeline.py backfill.py source.py trend.py ./
 
# Set entry point 
CMD ["python", "/app/pipeline.py"] 