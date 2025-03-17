FROM python:3.10-slim-buster

# Set working directory inside the container
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy pyproject.toml and poetry.lock first for caching layers
COPY pyproject.toml poetry.lock* ./

# Install project dependencies using Poetry
RUN poetry install --no-root --no-interaction --only main

# Copy the rest of the project files into the container
COPY . .

# Make run.sh executable
RUN chmod +x run.sh

# Set the command to run when the container starts
ENTRYPOINT ["sh","/app/run.sh"]

# # --- Builder Stage ---
# FROM python:3.10-slim-buster AS builder

# WORKDIR /app

# # Install Poetry - needed only for build stage
# RUN pip install --no-cache-dir poetry

# # Copy only project definition files for dependency resolution
# COPY pyproject.toml poetry.lock* ./

# # Install production dependencies only - using Poetry in builder stage
# RUN poetry install --no-root --no-interaction --only main

# # Copy application code - after dependencies are installed to leverage caching
# COPY . .

# # --- Runner Stage ---
# FROM python:3.10-slim-buster AS runner

# WORKDIR /app

# # Copy only the application and virtual environment from the builder stage
# COPY --from=builder /app/.venv ./.venv
# COPY --from=builder /app .

# # Make run.sh executable in the runner stage
# RUN chmod +x run.sh

# # Set entrypoint for the runner stage
# ENTRYPOINT ["sh","/app/run.sh"]