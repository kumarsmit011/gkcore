# Using python:3.12-slim
FROM python:3.12-slim

# Set environment variables
ENV POETRY_VERSION=1.8.4
ENV POETRY_HOME="/.poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
  build-essential libpq-dev curl && \
  curl -sSL https://install.python-poetry.org | python3 - && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /gkcore

# Copy the entire project directory
COPY . .

# Build and install the project
RUN poetry build && pip install dist/*.whl

# Create non-root user
RUN adduser --disabled-password --gecos '' gkuser

# Set permissions
RUN chown -R gkuser:gkuser /gkcore
USER gkuser

# Copy and configure entrypoint script
RUN chmod +x /gkcore/entrypoint.sh

# Expose Pyramid port (default: 6543)
EXPOSE 6543

# Define entrypoint
ENTRYPOINT ["/gkcore/entrypoint.sh"]

# Add a healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:6543 || exit 1
