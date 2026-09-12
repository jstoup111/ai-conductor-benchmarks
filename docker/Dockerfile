FROM node:26-bookworm-slim AS node
FROM ruby:3.4.8-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl ca-certificates libyaml-dev libssl-dev pkg-config \
    libvips sqlite3 chromium chromium-driver python3 tmux bubblewrap ripgrep procps \
    && rm -rf /var/lib/apt/lists/*
ARG CLAUDE_VERSION=2.1.267
ARG CODEX_VERSION=0.154.0
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_VERSION} @openai/codex@${CODEX_VERSION}
ENV BUNDLE_PATH=/usr/local/bundle DATABASE_ADAPTER=sqlite \
    HOME=/home/bench CODEX_HOME=/home/bench/.codex CLAUDE_CONFIG_DIR=/home/bench/.claude \
    PATH=/home/bench/.local/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
WORKDIR /opt/fizzy
COPY fixtures/fizzy/ ./
RUN bundle install
RUN useradd --create-home --uid 1000 --shell /bin/bash bench && \
    chown -R bench:bench /opt/fizzy /usr/local/bundle
COPY docker/prepare-app /usr/local/bin/prepare-app
USER bench
WORKDIR /workspace
CMD ["bash"]
# Available to both arms when the agreed endpoint includes publication.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends gh && rm -rf /var/lib/apt/lists/*
USER bench
