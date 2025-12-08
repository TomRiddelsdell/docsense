# Development Container Configuration

This directory contains the VS Code dev container configuration for the Portfolio Platform project.

## 🏗️ Architecture

## Universal Image with Dev Container Features

- Uses Microsoft Universal dev container image (multi-language support)
- Languages included: Node.js, Python, Java, and system tools
- CLI tools installed via dev container features and setup script
- Configured for Event-Sourced Microservices development
- Optimized for our tech stack: TypeScript, Next.js, PostgreSQL, Kafka

## 🔧 What's Included

### Core Languages & Tools (Via Universal Image + Features)

- **Node.js**: Latest LTS with npm/pnpm package managers
- **Python**: Latest version with pip package manager
- **Java**: JDK 24 (Microsoft distribution)
- **AWS CLI**: Official AWS command line interface
- **Terraform CLI**: Infrastructure as Code deployment
- **Docker**: Docker-outside-of-docker for container operations

### Additional CLI Tools (Installed via setup-optimized.sh)

- **Doppler CLI**: Centralized secrets management
- **Wrangler CLI**: Cloudflare Workers deployment
- **Neon CLI**: PostgreSQL database management
- **Confluent CLI**: Apache Kafka management
- **GitHub CLI**: GitHub API and repository operations

### Utility Scripts

- **`setup-optimized.sh`**: Lightweight setup script (runs automatically)
- **`inject-doppler-env.sh`**: Manual secret injection
- **`verify-cli-auth.sh`**: Authentication verification
- **`validate-security.sh`**: Security scanning for credential leaks

### Documentation

- **`README.md`**: This file - dev container configuration guide

### VS Code Extensions

- GitHub Copilot & Chat
- TypeScript/JavaScript development
- React/Next.js support
- Testing (Playwright, Vitest)
- Database tools (PostgreSQL)
- Infrastructure (Terraform, Docker)
- Documentation (Markdown)

### MCP Server Integration

- **GitHub MCP**: Official @modelcontextprotocol/server-github
- **Neon MCP**: Official @neondatabase/mcp-server-neon
- **AWS CLI MCP**: Official @modelcontextprotocol/server-aws-cli

## 🚀 Getting Started

1. **Environment Setup**:

   ```bash
   cp .env.example .env
   # Fill in your actual values in .env
   ```

2. **Open in Dev Container**:
   - Use VS Code Command Palette
   - Run: "Dev Containers: Reopen in Container"

3. **Post-Setup Commands** (run automatically):

   ```bash
   # The setup-optimized.sh script installs additional CLI tools
   # and configures git settings
   ```

4. **Verify Installation**:

   ```bash
   doppler --version
   wrangler --version
   terraform --version
   neonctl --version
   confluent version
   ```

## 📁 Directory Structure Created

The setup script creates the standard monorepo structure:

- `packages/` - Shared libraries and components
- `services/` - Domain microservices
- `apps/` - Frontend applications
- `contracts/` - API and event contracts
- `tests/` - All test types
- `infra/` - Infrastructure as code

## 🔐 Environment Variables

All sensitive values are loaded from the host environment or Doppler.
See `.env.example` for required variables.

### Authentication Flow

1. **Host Variables** (non-sensitive, in `~/.bashrc` and `~/.profile`)
   - `DEV_EMAIL` → Maps to all service email variables
   - `DEV_USER_NAME` → Maps to Git configuration
   - `DOPPLER_TOKEN` → Service token for secrets access

2. **Doppler Secrets** (sensitive API keys, stored securely)
   - `CLOUDFLARE_API_KEY` / `NEON_API_KEY` / `GITHUB_TOKEN`
   - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
   - `CONFLUENT_CLOUD_API_KEY` / `CONFLUENT_CLOUD_API_SECRET`

3. **Automatic Setup**
   - Host variables inherited by container at startup
   - Doppler secrets injected as environment variables
   - All CLI tools authenticate automatically

### Troubleshooting Authentication

```bash
# Verify all CLI authentications
.devcontainer/verify-cli-auth.sh

# Manually inject Doppler secrets if needed
source .devcontainer/inject-doppler-env.sh

# Check for credential leaks before commits
.devcontainer/validate-security.sh
```

## 🗑️ Cleaned Up Components

**Recently Removed**:

- **Dockerfile**: No longer needed since using Universal image directly
- **setup.sh**: Replaced by setup-optimized.sh for faster container startup

**Previous Complex Setup** (backed up as \*.backup):

- Multi-container Docker Compose setup
- Custom MCP server containers
- Complex environment variable duplication
- Unnecessary service dependencies

**Why Simplified**:

- Official MCP servers are more reliable
- Single container is faster to start
- Less configuration complexity
- Easier troubleshooting
- Better VS Code integration

## 🎯 Ready for Phase 0

This configuration supports the implementation plan:

- All required CLI tools
- Proper MCP server integration
- Environment variable management
- Infrastructure deployment tools
- Database and message bus clients

Perfect foundation for executing the 8-12 week implementation roadmap!
