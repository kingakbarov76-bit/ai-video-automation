FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir requests pillow numpy
RUN git clone --depth 1 --branch live https://github.com/kingakbarov76-bit/ai-video-automation /app
RUN useradd -m -u 1000 user && mkdir -p /home/user/app && chown -R user /home/user
USER user
WORKDIR /home/user/app
ENV PORT=7860 PYTHONPATH=/app
CMD ["python", "/app/stream/app.py"]
