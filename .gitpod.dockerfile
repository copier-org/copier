FROM gitpod/workspace-full

RUN sudo apt-get update \
    && sudo apt-get install -y \
        fish \
        pipx \
        python3-venv \
    && sudo rm -rf /var/lib/apt/lists/*

RUN pipx install poethepoet
RUN pipx install pdm
RUN pipx install pre-commit

ENTRYPOINT ["env", "PIP_USER=no"]
