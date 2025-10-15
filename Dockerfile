FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install Python dependencies using uv
RUN pip install uv && uv sync

# Force opencv-python-headless to be imported (both packages will be installed due to layoutparser dependency)
# The headless version will be used if it's the same package name

# Create data directories
RUN mkdir -p /app/data/jails-data/handwritten_party

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV OPENCV_IO_ENABLE_OPENEXR=1
ENV QT_QPA_PLATFORM=offscreen

# Default command
CMD ["uv", "run", "--no-sync", "python", "src/jail-events/main.py", "--help"]