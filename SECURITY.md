# Security Policy

## Supported Versions

We take security seriously and actively maintain security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in VRChat MCP, please help us by reporting it responsibly.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:
- **Email**: security@sandraschi.com
- **Subject**: [SECURITY] VRChat MCP Vulnerability Report

### What to Include

When reporting a security vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Impact**: What an attacker could achieve by exploiting this vulnerability
3. **Steps to Reproduce**: Detailed steps to reproduce the issue
4. **Proof of Concept**: If possible, include a proof of concept
5. **Environment**: Your system details (OS, Python version, etc.)
6. **Contact Information**: How we can reach you for follow-up questions

### Response Timeline

We will acknowledge your report within 48 hours and provide a more detailed response within 7 days indicating our next steps.

We will keep you informed about our progress throughout the process of fixing the vulnerability.

### Disclosure Policy

- We follow a coordinated disclosure process
- We will credit you (if desired) once the vulnerability is fixed and disclosed
- We will not disclose vulnerability details until a fix is available
- We aim to release fixes as quickly as possible, typically within 30 days

## Security Considerations

### Network Communication
- OSC communication uses UDP and may not be encrypted
- FastAPI HTTP interface supports HTTPS when properly configured
- All network communications should be secured in production environments

### Data Handling
- Avatar parameters and conversation data may contain sensitive information
- Log files may contain OSC parameter values
- Ensure proper access controls when deploying

### Dependencies
- We regularly update dependencies to address security vulnerabilities
- Use `pip-audit` or similar tools to check for known vulnerabilities
- Only install from trusted sources

## Security Best Practices for Users

### Installation
```bash
# Install in a virtual environment
python -m venv vrchat_mcp_env
source vrchat_mcp_env/bin/activate  # On Windows: vrchat_mcp_env\Scripts\activate

# Install the package
pip install vrchat-mcp
```

### Configuration
- Use strong, unique passwords if authentication is enabled
- Configure firewalls to restrict network access as needed
- Use HTTPS in production environments
- Regularly rotate any API keys or tokens

### Operation
- Monitor logs for unusual activity
- Keep the system and dependencies updated
- Run security audits regularly
- Limit network exposure in sensitive environments

### VRChat Integration
- OSC communication is local network only by default
- VRChat itself handles avatar data security
- Be aware that OSC parameters may be visible on local network

## Security Updates

Security updates will be:
- Released as patch versions (e.g., 0.1.1, 0.1.2)
- Documented in CHANGELOG.md under security sections
- Announced through GitHub Security Advisories
- Tagged with appropriate CVE identifiers when applicable

## Contact

For security-related questions or concerns:
- **Email**: security@sandraschi.com
- **GitHub**: [Create a private security advisory](https://github.com/sandraschi/vrchat-mcp/security/advisories/new)

Thank you for helping keep VRChat MCP secure! 🔒


