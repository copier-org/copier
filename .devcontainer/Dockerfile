# renovate: datasource=github-tags depName=devbox packageName=jetify-com/devbox
ARG DEVBOX_VERSION=0.16.0
FROM jetpackio/devbox:${DEVBOX_VERSION}

WORKDIR /code

COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.json devbox.json
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.lock devbox.lock

# Install the Devbox environment
RUN devbox install && nix-store --gc

# Configure the project's virtual env path to be outside the mounted workspace
# to avoid conflicts with the host env.
ENV UV_PROJECT_ENVIRONMENT=/code/.venv
