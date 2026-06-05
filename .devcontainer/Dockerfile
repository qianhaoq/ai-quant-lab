FROM mcr.microsoft.com/devcontainers/typescript-node:24-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-venv python3-pip \
  && rm -rf /var/lib/apt/lists/*
