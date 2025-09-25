FROM nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_PREFER_BINARY=1
ENV PYTHONUNBUFFERED=1
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

#Install Python, git and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    wget \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/bin/python3.12:$PATH"

# Create symbolic links for python3 and pip3
RUN ln -sf /usr/bin/python3.12 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip
RUN git clone https://github.com/comfyanonymous/ComfyUI

# Change working directory to ComfyUI
WORKDIR /ComfyUI

# Support for the network volume
ADD src/extra_model_paths.yaml ./

# Go back to the root
WORKDIR /

# Install uv (latest) using official installer and create isolated venv
RUN wget -qO- https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx \
    && uv venv /opt/dev-venv

# Use the virtual environment for all subsequent commands
ENV PATH="/opt/dev-venv/bin:${PATH}"

# Install Python runtime dependencies for the handler
RUN uv pip install runpod requests websocket-client

# Copy files after setting up the environment
COPY ./app-dev-test/ /app-dev-test
COPY ./workflow-data/ /workflow-data

# root directory
WORKDIR /

# clone ComfyUI in root directory
RUN git clone https://github.com/comfyanonymous/ComfyUI

# copy custom nodes to ComfyUI directory in Docker container
COPY ComfyUI/custom_nodes/ /ComfyUI/custom_nodes

# copy extra model paths to ComfyUI directory in Docker container
COPY src/extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml

RUN chmod -R 755 /app-dev-test
RUN chmod -R 755 /workflow-data
RUN chmod -R 755 /ComfyUI

# Copy và giải nén venv trực tiếp
COPY venv.tar.gz /tmp/venv.tar.gz
RUN mkdir -p /environment-comfyui/venv \
    && tar -xzf /tmp/venv.tar.gz -C /environment-comfyui/venv \
    && rm /tmp/venv.tar.gz \
    && chmod -R 755 /environment-comfyui/venv

# Install Python dependencies cho dev programs
RUN uv pip install "aiohttp>=3.8.0" "requests>=2.28.0" "Pillow>=9.0.0" "ujson>=5.0.0" "colorlog>=6.7.0"

# Expose ports  
EXPOSE 8188 8000 8001

CMD ["/bin/bash"]