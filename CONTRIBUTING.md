# Contributing to Krock

Welcome! We are excited that you’re interested in contributing to **Krock**. Whether you’re looking to fix a small bug, improve documentation, or propose a new architectural feature, your help is appreciated.

## Getting Started
To start developing on Krock:

1. **Fork the Repository:** Click the 'Fork' button at the top right of the [Krock GitHub repository](https://github.com/Rohit-Solanki-6105/krock).
2. **Clone your fork:**
```bash
   git clone [https://github.com/](https://github.com/)<your-username>/krock.git
   cd krock
   ```
3. **Install Dependencies:**
   * **Python Environment:** Ensure you have Python 3.10+ installed. Set up a virtual environment:
```bash
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate
     pip install -r requirements.txt
```
**Node/npm:** Ensure your environment is ready for the framework's frontend components.

## How to Contribute

### 1. Reporting Issues
Before opening a new issue, please check the [Issue Tracker](https://github.com/Rohit-Solanki-6105/krock/issues) to see if it has already been reported. 

When filing an issue, please include:
* **Environment:** Python version, OS, and Node version.
* **Steps to Reproduce:** Provide a minimal code snippet or steps that cause the behavior.
* **Expected vs. Actual Behavior:** What did you expect to happen, and what happened instead?

### 2. Suggesting Features
If you have an idea to improve Krock's cross-stack capabilities or routing, start by opening an issue labeled as `feature-request`. Please provide:
* A clear description of the feature.
* Why this helps the Krock ecosystem.
* A rough outline of the proposed API or implementation.

### 3. Pull Requests (PRs)
We welcome PRs for bug fixes and feature additions.
1. **Create a Branch:** `git checkout -b feature/your-feature-name` or `fix/issue-description`.
2. **Test Your Changes:** Ensure your code works as expected. If adding a new feature, include a small test case in the `/tests` directory.
3. **Keep it Atomic:** Try to keep PRs focused on a single issue or feature.
4. **Submit:** Push to your fork and submit a PR to the main repository.

## Development Standards
* **Python Code:** Follow PEP 8 guidelines.
* **Frontend:** Maintain compatibility with current React 19 standards and the existing Next.js-inspired file structure.
* **Documentation:** If you add a feature, please update the README or the relevant documentation files.

## Code of Conduct
By participating in this project, you agree to maintain a respectful and constructive environment. Harassment or exclusionary language will not be tolerated.

## Need Help?
If you are stuck, feel free to reach out via [GitHub Issues](https://github.com/Rohit-Solanki-6105/krock/issues) or directly contact the maintainers. We are happy to help you get your environment set up or discuss technical blockers.