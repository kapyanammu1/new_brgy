# Use an official Python runtime as a parent image
FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the font files into the container
COPY Arial.ttf /usr/share/fonts/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Other dependencies your application needs \
    # For example, if you need to install fonts, you might need fontconfig and libfreetype6-dev \
    fontconfig \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app/
COPY . .

EXPOSE 8000

# Run the application when the container launch
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

