FROM python:3.9-slim

ARG USER=copier
ENV APP_DIR=/copier

RUN apt-get update -y \
    && apt-get install --no-install-recommends build-essential gcc git -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home ${USER}

RUN mkdir -p ${APP_DIR} && chown -R ${USER}:${USER} ${APP_DIR}

WORKDIR ${APP_DIR}

USER ${USER}

ENV PATH=/home/${USER}/.local/bin:$PATH


RUN pip install --no-cache-dir --user pipx; \
    pipx ensurepath; \
    pipx install copier; \
    pipx install invoke; \
    pipx install pre-commit;

ENTRYPOINT ["copier"]
