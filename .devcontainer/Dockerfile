# Portfolio Platform Development Container
# Optimized for event-sourced microservices development
# Using Universal Dev Container 4.x with Ubuntu 24.04 (Noble) for modern glibc 2.39 and comprehensive tooling
FROM mcr.microsoft.com/devcontainers/universal:4-linux

# Set environment variables for build
ENV DEBIAN_FRONTEND=noninteractive

# Configure npm global directory following Node.js Docker best practices
# This avoids permission issues by using a shared location accessible to both root and codespace users
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=/usr/local/share/npm-global/bin:$PATH

# Update package lists and install essential system tools (cached layer)
RUN apt-get update -y && apt-get install -y \
    curl \
    wget \
    unzip \
    jq \
    git \
    build-essential \
    gnupg \
    lsb-release \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Set up npm global directory with proper permissions
RUN mkdir -p /usr/local/share/npm-global \
    && chown codespace:nvm /usr/local/share/npm-global \
    && chmod 755 /usr/local/share/npm-global

# Install CLI tools following official best practices
RUN echo "🔧 Installing CLI tools for Portfolio Platform..." && \
    # Install Doppler CLI (Secrets Management)
    echo "🔐 Installing Doppler CLI..." && \
    curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | sh && \
    # Install Confluent CLI (Kafka Management)
    echo "📊 Installing Confluent CLI..." && \
    cd /tmp && \
    curl -L --http1.1 https://cnfl.io/cli | sh -s -- latest && \
    mv bin/confluent /usr/local/bin/confluent && \
    # Install npm-based CLI tools using configured global prefix (runs as root but installs to shared location)
    echo "☁️ Installing npm-based CLI tools globally..." && \
    npm install -g pnpm@latest wrangler@latest neonctl@latest && \
    # Install Claude CLI (AI-Powered Coding Assistant via npm)
    echo "🤖 Installing Claude CLI..." && \
    npm install -g @anthropic-ai/claude-code && \
    # Install additional development tools
    echo "🛠️ Installing additional development utilities..." && \
    npm install -g @playwright/test eslint prettier typescript ts-node nodemon turbo@latest && \
    # Install Avro tools for event schema management
    echo "📋 Installing Avro tools for event sourcing..." && \
    npm install -g avro-typescript avro-js @kafkajs/confluent-schema-registry

# Reset to interactive mode
ENV DEBIAN_FRONTEND=

# Verification layer (will show in build output and help debug issues)
RUN echo "✅ Installation verification:" && \
    echo "  • Node.js: $(node --version)" && \
    echo "  • npm: $(npm --version)" && \
    echo "  • pnpm: $(pnpm --version)" && \
    echo "  • Doppler: $(doppler --version 2>/dev/null || echo 'MISSING')" && \
    echo "  • Claude CLI: $(claude --version 2>/dev/null || echo 'MISSING')" && \
    echo "  • Confluent CLI: $(confluent version 2>/dev/null | head -n1 || echo 'MISSING')" && \
    echo "  • Terraform: $(terraform --version 2>/dev/null | head -n1 || echo 'from features')" && \
    echo "  • AWS CLI: $(aws --version 2>/dev/null | head -n1 || echo 'from features')" && \
    echo "  • GitHub CLI: $(gh --version 2>/dev/null | head -n1 || echo 'from base image')" && \
    echo "  • Git: $(git --version)" && \
    # Check npm packages using global prefix
    echo "  • Wrangler: $(wrangler --version 2>/dev/null || echo 'MISSING')" && \
    echo "  • Neon CLI: $(neonctl --version 2>/dev/null || echo 'MISSING')" && \
    echo "  • ESLint: $(eslint --version 2>/dev/null || echo 'MISSING')" && \
    echo "  • TypeScript: $(tsc --version 2>/dev/null || echo 'MISSING')" && \
    # Fail the build if critical tools are missing
    echo "🔍 Verifying critical CLI tools are accessible..." && \
    doppler --version > /dev/null && echo "  ✅ Doppler OK" && \
    claude --version > /dev/null && echo "  ✅ Claude CLI OK" && \
    wrangler --version > /dev/null && echo "  ✅ Wrangler OK" && \
    neonctl --version > /dev/null && echo "  ✅ Neon CLI OK" && \
    confluent version > /dev/null && echo "  ✅ Confluent CLI OK" && \
    eslint --version > /dev/null && echo "  ✅ ESLint OK" && \
    tsc --version > /dev/null && echo "  ✅ TypeScript OK"

# Switch back to codespace user for runtime
USER codespace