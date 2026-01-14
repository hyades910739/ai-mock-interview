# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
# The .dockerignore file will prevent copying unnecessary files
COPY . .

# Install the application using setup.py
RUN pip install .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variables.
# The OPENAI_API_KEY must be provided at runtime.
ENV PORT=8000
ENV INTERVIEWER_MODEL_NAME="gpt-5-nano-2025-08-07"
ENV TUTOR_MODEL_NAME="gpt-5-nano-2025-08-07"

# ENV OPENAI_API_KEY=""

# Run uvicorn server
CMD ["uvicorn", "ai_mock_interview.main:app", "--host", "0.0.0.0", "--port", PORT]
