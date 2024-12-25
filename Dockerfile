# Use Python 3.10 slim image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry==1.5.1

# Copy only the pyproject.toml and poetry.lock files
COPY pyproject.toml poetry.lock ./

# Install project dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the rest of the application's code
COPY . .

# Command to run tests
CMD ["poetry", "run", "pytest", "tests/"]
