# Security Policy

## Scope and Intent

PhantomScan (Phantom Dependency Radar) is a **defensive security research tool** designed to:

- Monitor public package registries (PyPI, npm) for suspicious publications
- Generate threat intelligence feeds for security teams
- Provide hunt queries for detecting installations of risky packages
- Support incident response and supply-chain risk assessment

## Responsible Use Guidelines

### ✅ Permitted Use

- Running the radar against public package registries (PyPI, npm) using their official APIs
- Analyzing package metadata to assess supply-chain risk
- Generating internal threat intelligence feeds
- Creating detection rules for security monitoring
- Sharing anonymized statistics and trends for research purposes
- Contributing improvements to scoring heuristics

### ❌ Prohibited Use

- **NEVER publish packages to PyPI, npm, or any registry** for testing purposes without explicit authorization
- **NEVER probe or scan systems** beyond public package metadata endpoints
- **NEVER use this tool to conduct attacks** or deploy malicious code
- **NEVER harass package maintainers** based on radar findings without thorough investigation
- **DO NOT share raw candidate lists publicly** without verifying false positives (to avoid defaming legitimate packages)

## Ethical Considerations

1. **False Positives**: Scoring heuristics are probabilistic. Always manually verify findings before taking action.

2. **Maintainer Communication**: If you discover a genuine malicious package, report it to the registry security team (security@pypi.org, security@npmjs.com), not the maintainer.

3. **Responsible Disclosure**: Do not publish details of active supply-chain attacks until they are remediated and affected users are notified.

4. **Rate Limiting**: The tool implements respectful rate limiting. Do not modify the code to bypass these limits.

## Reporting Security Issues

If you discover a security vulnerability in PhantomScan itself:

- **Email**: security@example.com (replace with actual contact)
- **Subject**: [SECURITY] PhantomScan Vulnerability Report
- **Include**: Detailed description, reproduction steps, and impact assessment

We aim to respond within 48 hours and provide a fix within 7 days for critical issues.

## Legal Compliance

Users are responsible for ensuring their use of this tool complies with:

- Applicable laws and regulations in their jurisdiction
- Terms of service for PyPI (https://pypi.org/policy/terms-of-use/)
- Terms of service for npm (https://docs.npmjs.com/policies/terms)
- Their organization's security and data policies

## Disclaimer

This tool is provided "as is" without warranty. The authors are not responsible for misuse or any consequences arising from the use of this tool. By using PhantomScan, you agree to these terms and commit to responsible, ethical security research.
