FROM python:3.11-slim

# Set environment variables to optimize Python 
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies (needed for OCR and C-extensions)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-cpp-dev \
    pkg-config \
    poppler-utils \
    # Add other binary dependencies if your OCR tooling or python packages require them
    tesseract-ocr \
    libtesseract-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements.txt and install dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt


# Copy the rest of the application
COPY . .

# Create a non-root user for security
RUN useradd -m fastfin && chown -R fastfin:fastfin /app
USER fastfin

# Expose Streamlit and Flask ports
EXPOSE 8501 5000

# Default command acts as a placeholder; typically overridden by docker-compose
CMD ["python", "api.py"]
