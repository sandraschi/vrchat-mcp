# Contributing to VRChat MCP

Thank you for your interest in contributing to VRChat MCP! This document provides guidelines and information for contributors.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Documentation](#documentation)

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** from `master`
4. **Make your changes**
5. **Run tests** to ensure everything works
6. **Submit a pull request**

## Development Setup

### Prerequisites
- Python 3.8+
- Git
- (Optional) Claude Desktop for testing MCP integration

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/vrchat-mcp.git
cd vrchat-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Verify Setup
```bash
# Run tests
python -m pytest

# Run linting
black --check src/
isort --check-only src/
mypy src/
```

## Project Structure

```
vrchat-mcp/
├── src/vrchat_mcp/           # Main package
│   ├── __init__.py          # FastMCP app initialization
│   ├── cli.py               # Command-line interface
│   ├── server.py            # Thin server entry point
│   ├── models.py            # Pydantic models
│   ├── tools/               # Tool implementations
│   │   ├── __init__.py
│   │   ├── avatar/         # Avatar management tools
│   │   ├── osc/            # OSC communication tools
│   │   ├── npc/            # NPC conversation tools
│   │   └── shared/         # Shared utilities
│   ├── plugins/            # Plugin system
│   ├── web/                # Web interface assets
│   └── websocket_server.py # Debug UI server
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── local/             # Local test scripts
├── prompts/               # Example prompt templates
├── scripts/               # Utility scripts
├── dxt_manifest.json      # DXT packaging configuration
├── pyproject.toml         # Python project configuration
└── README.md             # Project documentation
```

## Development Workflow

### 1. Choose an Issue
- Check existing [GitHub Issues](https://github.com/sandraschi/vrchat-mcp/issues)
- Comment on the issue to indicate you're working on it
- Create a new issue if your contribution doesn't have one

### 2. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes
- Follow the coding standards below
- Write tests for new functionality
- Update documentation as needed
- Keep commits focused and descriptive

### 4. Run Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src/vrchat_mcp

# Run specific test categories
python -m pytest -m unit
python -m pytest -m integration
```

### 5. Update Documentation
- Update README.md for user-facing changes
- Update CHANGELOG.md following Keep a Changelog format
- Add docstrings to new functions/classes
- Update type hints

## Testing

### Running Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With verbose output
pytest -v

# With coverage report
pytest --cov=src/vrchat_mcp --cov-report=html
```

### Writing Tests
- Unit tests should test individual functions/classes
- Integration tests should test component interactions
- Use descriptive test names and docstrings
- Mock external dependencies appropriately
- Aim for >80% code coverage

### Local Testing Scripts
```bash
# Test MCP interface locally
python tests/local/test_mcp_interface.py

# Test FastAPI interface locally
python tests/local/test_fastapi_interface.py

# Run PowerShell test suite
powershell -ExecutionPolicy Bypass -File tests/local/run_mcp_tests.ps1
```

## Submitting Changes

### Pull Request Process
1. **Ensure tests pass** locally
2. **Update CHANGELOG.md** with your changes
3. **Rebase on master** to resolve conflicts
4. **Push your branch** to GitHub
5. **Create a Pull Request** with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues
   - Screenshots/videos for UI changes

### PR Review Process
- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged
- Your contribution will be acknowledged in the changelog

## Coding Standards

### Python Style
- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Add type hints to function parameters and return values

### Code Quality
- Write descriptive variable and function names
- Add docstrings to all public functions, classes, and modules
- Keep functions focused on single responsibilities
- Handle errors gracefully with appropriate logging

### FastMCP Tool Registration
```python
@mcp.tool()
async def my_tool(param1: str, param2: int = 0) -> Dict[str, Any]:
    """
    Description of what the tool does.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)

    Returns:
        Dictionary containing the result
    """
    # Implementation here
    pass
```

### Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Start with a capital letter
- Keep the first line under 50 characters
- Add detailed description if needed

## Documentation

### Code Documentation
- All public functions need docstrings
- Include parameter descriptions and types
- Document return values and exceptions
- Update README.md for user-facing changes

### API Documentation
- FastAPI automatically generates OpenAPI docs at `/api/docs`
- Tool descriptions appear in Claude Desktop
- Keep descriptions clear and actionable

### Changelog
- Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
- Add entries under appropriate sections (Added, Changed, Fixed, etc.)
- Include issue/PR references where applicable

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/sandraschi/vrchat-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sandraschi/vrchat-mcp/discussions)
- **Documentation**: Check the `docs/` directory and README.md

Thank you for contributing to VRChat MCP! 🎉


