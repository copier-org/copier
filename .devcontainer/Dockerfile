FROM ghcr.io/jdx/mise:2026.11.12-debian

RUN useradd --create-home --uid 1000 --shell /bin/bash vscode \
    && chown -R vscode:vscode /mise

RUN echo 'eval "$(mise activate bash)"' >> /home/vscode/.bashrc

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*
