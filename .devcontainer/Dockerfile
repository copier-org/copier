# renovate: datasource=github-tags depName=devbox packageName=jetify-com/devbox
ARG DEVBOX_VERSION=0.14.2
FROM jetpackio/devbox:${DEVBOX_VERSION}

WORKDIR /code

COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.json devbox.json
COPY --chown=${DEVBOX_USER}:${DEVBOX_USER} devbox.lock devbox.lock

# Install the Devbox environment
RUN devbox install && nix-store --gc
