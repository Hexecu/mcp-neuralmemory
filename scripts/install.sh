#!/bin/bash
#
# MCP-KG-Memory Quick Install Script
# 
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/your-org/mcp-kg-memory/main/scripts/install.sh | bash
#   OR
#   ./scripts/install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
print_info() { echo -e "${BLUE}ℹ ${NC}$1"; }
print_success() { echo -e "${GREEN}✓ ${NC}$1"; }
print_warning() { echo -e "${YELLOW}! ${NC}$1"; }
print_error() { echo -e "${RED}✗ ${NC}$1"; }

# Header
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          🧠 MCP-KG-Memory Quick Install                  ║"
echo "║          Memory/Knowledge Graph for AI Assistants        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python 3.11+ is required. Found: Python $PYTHON_VERSION"
    exit 1
fi
print_success "Python $PYTHON_VERSION detected"

# Check Docker
print_info "Checking Docker..."
if command -v docker &> /dev/null; then
    print_success "Docker is installed"
    DOCKER_AVAILABLE=true
else
    print_warning "Docker not found. Local Neo4j will not be available."
    DOCKER_AVAILABLE=false
fi

# Determine install location
INSTALL_DIR="${MCP_KG_INSTALL_DIR:-$HOME/.mcp-kg-memory}"

if [ -d "$INSTALL_DIR" ]; then
    print_warning "Installation directory exists: $INSTALL_DIR"
    read -p "Remove and reinstall? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        print_info "Using existing installation"
    fi
fi

# Clone or update repository
if [ ! -d "$INSTALL_DIR" ]; then
    print_info "Cloning repository..."
    git clone --depth 1 https://github.com/your-org/mcp-kg-memory.git "$INSTALL_DIR" 2>/dev/null || {
        print_warning "Could not clone from GitHub. Is this a local install?"
        
        # Check if we're already in the repo
        if [ -f "server/pyproject.toml" ]; then
            INSTALL_DIR="$(pwd)"
            print_info "Using current directory: $INSTALL_DIR"
        elif [ -f "../server/pyproject.toml" ]; then
            INSTALL_DIR="$(cd .. && pwd)"
            print_info "Using parent directory: $INSTALL_DIR"
        else
            print_error "Cannot find mcp-kg-memory repository"
            exit 1
        fi
    }
fi

cd "$INSTALL_DIR/server"

# Create virtual environment
print_info "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
print_success "Virtual environment created"

# Install dependencies
print_info "Installing dependencies..."
pip install --upgrade pip -q
pip install -e . -q
print_success "Dependencies installed"

# Verify installation
print_info "Verifying installation..."
if kg-mcp --help > /dev/null 2>&1; then
    print_success "kg-mcp command available"
else
    print_error "Installation verification failed"
    exit 1
fi

# Success message
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    ✓ Installation Complete               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "  1. Run the setup wizard:"
echo "     ${GREEN}source $INSTALL_DIR/server/.venv/bin/activate${NC}"
echo "     ${GREEN}kg-mcp-setup${NC}"
echo ""
echo "  2. Or manually configure:"
echo "     ${GREEN}cd $INSTALL_DIR${NC}"
echo "     ${GREEN}cp .env.example .env${NC}"
echo "     # Edit .env with your credentials"
echo ""
echo "  3. Start the server:"
echo "     ${GREEN}kg-mcp --transport http${NC}"
echo ""
echo "Documentation: ${BLUE}$INSTALL_DIR/README.md${NC}"
echo ""
