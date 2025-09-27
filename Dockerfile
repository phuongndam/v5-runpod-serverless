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

# Go back to the root
WORKDIR /

# Install uv (latest) using official installer and create isolated venv
RUN wget -qO- https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx \
    && uv venv /opt/dev-venv

# Use the virtual environment for all subsequent commands
ENV PATH="/opt/dev-venv/bin:${PATH}"

COPY ./requirements.txt /tmp/requirements.txt
RUN uv pip install -r /tmp/requirements.txt
RUN rm /tmp/requirements.txt

# Copy files after setting up the environment
COPY ./app/ /app
COPY ./workflow-data/ /workflow-data

# root directory
WORKDIR /

# clone ComfyUI in root directory
RUN git clone https://github.com/comfyanonymous/ComfyUI

# copy custom nodes to ComfyUI directory in Docker container
COPY ./custom_nodes/ /ComfyUI/custom_nodes
COPY ./test_input.json /test_input.json

# copy extra model paths to ComfyUI directory in Docker container
COPY src/extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml

RUN chmod -R 755 /app
RUN chmod -R 755 /workflow-data
RUN chmod -R 755 /ComfyUI
RUN chmod -R 755 /test_input.json

# Copy và giải nén venv trực tiếp
COPY venv.tar.gz /tmp/venv.tar.gz
RUN mkdir -p /environment-comfyui/venv \
    && tar -xzf /tmp/venv.tar.gz -C /environment-comfyui/venv \
    && rm /tmp/venv.tar.gz \
    && chmod -R 755 /environment-comfyui/venv

# Expose ports
EXPOSE 8188 8000 8001 8002

CMD ["app/start.sh"]