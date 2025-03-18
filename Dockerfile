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

