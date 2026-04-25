FROM python:3.12-slim
WORKDIR /app

# Install system build dependencies required by PyAV, dlib, and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    build-essential \
    cmake \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

COPY jarvis/ ./jarvis/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "jarvis/main.py"]
