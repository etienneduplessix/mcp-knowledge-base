# Project Coding Standards

## Overview

This document outlines the coding standards and best practices for our project.

## Python Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use docstrings for all public functions and classes

### Naming Conventions
- Classes: PascalCase (e.g., `MyClass`)
- Functions: snake_case (e.g., `my_function`)
- Constants: UPPER_CASE (e.g., `MAX_SIZE`)
- Private attributes: _leading_underscore

### Error Handling
- Use specific exception types
- Always clean up resources with context managers
- Log errors with appropriate severity levels

## Testing
- Write unit tests for all new features
- Maintain at least 80% code coverage
- Use pytest for testing framework

## Git Workflow
- Create feature branches from `main`
- Use conventional commit messages
- Require code review before merging
