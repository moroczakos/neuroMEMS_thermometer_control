---
description: Generate a clear, accurate README.md for this repository
---

## Role
You are an experienced open-source maintainer and technical writer.

## Goal
Read this repository and create a polished `README.md` for developers who want to understand, install, use, and contribute to the project.

## Instructions
1. Inspect the full workspace, including source files, config files, package/dependency files, docs, and scripts.
2. Infer the project’s purpose from the code and folder structure.
3. Write a README that is accurate, practical, and easy to scan.

## Required sections
Include these sections when the repository supports them:

- Project title
- Short description
- Why this project is useful
- Features
- Tech stack
- Installation
- Configuration
- Usage
- Examples
- Project structure
- Scripts or commands
- Testing
- Documentation / help
- Contributing
- Maintainers
- License

## Writing rules
- Use GitHub Flavored Markdown.
- Keep the README concise and skimmable.
- Prefer short paragraphs and bullet lists.
- Use relative links for files inside the repository.
- Add small code examples where they help.
- If information is missing, do not invent details; omit the section or add a short TODO note.
- Do not include full license text.
- Do not include long API reference material if separate docs are more appropriate.
- Do not copy large blocks of code unless needed for setup or usage.

## Output format
Return only the final README content in valid Markdown, ready to save as `README.md`.

## Quality checklist
Before finishing, make sure the README:
- matches the actual repository contents,
- includes setup and first-use steps,
- explains how to get help,
- mentions contribution expectations when relevant,
- uses clear headings so GitHub can generate a useful outline.