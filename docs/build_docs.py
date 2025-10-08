#!/usr/bin/env python3
"""PAKE System Documentation Builder
Simple documentation builder that generates HTML from Markdown files.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import markdown


class DocumentationBuilder:
    """Simple documentation builder for PAKE System."""

    def __init__(self, source_dir: str = "docs", output_dir: str = "docs/_build"):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Configure markdown extensions
        self.md_extensions = [
            "markdown.extensions.toc",
            "markdown.extensions.tables",
            "markdown.extensions.codehilite",
            "markdown.extensions.fenced_code",
            "markdown.extensions.attr_list",
            "markdown.extensions.def_list",
            "markdown.extensions.footnotes",
            "markdown.extensions.md_in_html",
        ]

        self.md_config = {
            "markdown.extensions.codehilite": {
                "css_class": "highlight",
                "use_pygments": False,
            }
        }

    def build_documentation(self) -> None:
        """Build the complete documentation."""
        print("Building PAKE System documentation...")

        # Create output directory structure
        self._create_output_structure()

        # Build main documentation
        self._build_main_docs()

        # Build architecture documentation
        self._build_architecture_docs()

        # Build API documentation
        self._build_api_docs()

        # Generate index
        self._generate_index()

        # Copy static files
        self._copy_static_files()

        print(f"Documentation built successfully in {self.output_dir}")

    def _create_output_structure(self) -> None:
        """Create the output directory structure."""
        directories = [
            "architecture",
            "api",
            "user_guide",
            "development",
            "deployment",
            "troubleshooting",
            "static",
        ]

        for directory in directories:
            (self.output_dir / directory).mkdir(exist_ok=True)

    def _build_main_docs(self) -> None:
        """Build main documentation files."""
        main_files = ["README.md", "CONTRIBUTING.md", "CHANGELOG.md"]

        for file in main_files:
            source_file = self.source_dir / file
            if source_file.exists():
                file_path = Path(file)
                self._convert_markdown_to_html(
                    source_file, self.output_dir / f"{file_path.stem}.html"
                )

    def _build_architecture_docs(self) -> None:
        """Build architecture documentation."""
        arch_dir = self.source_dir / "architecture"
        if not arch_dir.exists():
            return

        for md_file in arch_dir.rglob("*.md"):
            relative_path = md_file.relative_to(arch_dir)
            output_path = (
                self.output_dir / "architecture" / relative_path.with_suffix(".html")
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._convert_markdown_to_html(md_file, output_path)

    def _build_api_docs(self) -> None:
        """Build API documentation."""
        # Generate API documentation from Python docstrings
        self._generate_api_from_docstrings()

    def _generate_api_from_docstrings(self) -> None:
        """Generate API documentation from Python docstrings."""
        api_docs = {
            "title": "PAKE System API Reference",
            "version": "1.0.0",
            "description": "Comprehensive API reference for the PAKE System",
            "endpoints": [],
        }

        # Scan Python files for API endpoints
        src_dir = Path("src")
        if src_dir.exists():
            for py_file in src_dir.rglob("*.py"):
                if "api" in str(py_file) or "service" in str(py_file):
                    self._extract_api_docs(py_file, api_docs)

        # Generate API documentation HTML
        api_html = self._generate_api_html(api_docs)
        with open(self.output_dir / "api" / "index.html", "w") as f:
            f.write(api_html)

    def _extract_api_docs(self, py_file: Path, api_docs: dict[str, Any]) -> None:
        """Extract API documentation from Python file."""
        try:
            with open(py_file) as f:
                content = f.read()

            # Simple extraction of class and function docstrings
            lines = content.split("\n")
            current_class = None
            current_function = None

            for i, line in enumerate(lines):
                if line.strip().startswith("class "):
                    current_class = line.strip().split("(")[0].replace("class ", "")
                elif line.strip().startswith("def ") and not line.strip().startswith(
                    "def _"
                ):
                    current_function = line.strip().split("(")[0].replace("def ", "")
                elif line.strip().startswith('"""') and current_function:
                    # Extract docstring
                    docstring_lines = []
                    j = i
                    while j < len(lines) and not lines[j].strip().endswith('"""'):
                        docstring_lines.append(lines[j])
                        j += 1
                    if j < len(lines):
                        docstring_lines.append(lines[j])

                    docstring = "\n".join(docstring_lines).strip('"""').strip()
                    if docstring:
                        api_docs["endpoints"].append(
                            {
                                "class": current_class,
                                "function": current_function,
                                "docstring": docstring,
                                "file": str(py_file),
                            }
                        )
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error processing {py_file}: {e}")

    def _generate_api_html(self, api_docs: dict[str, Any]) -> str:
        """Generate HTML for API documentation."""
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{api_docs["title"]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .endpoint {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .endpoint h3 {{ margin-top: 0; color: #333; }}
        .docstring {{ background: #f9f9f9; padding: 10px; border-radius: 3px; }}
        .file-info {{ font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <h1>{api_docs["title"]}</h1>
    <p><strong>Version:</strong> {api_docs["version"]}</p>
    <p>{api_docs["description"]}</p>

    <h2>API Endpoints</h2>
"""

        for endpoint in api_docs["endpoints"]:
            html += f"""
    <div class="endpoint">
        <h3>{endpoint["class"]}.{endpoint["function"]}</h3>
        <div class="docstring">
            <pre>{endpoint["docstring"]}</pre>
        </div>
        <div class="file-info">
            <strong>File:</strong> {endpoint["file"]}
        </div>
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def _convert_markdown_to_html(self, source_file: Path, output_file: Path) -> None:
        """Convert Markdown file to HTML."""
        try:
            with open(source_file) as f:
                markdown_content = f.read()

            # Convert markdown to HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=self.md_extensions,
                extension_configs=self.md_config,
            )

            # Wrap in HTML template
            full_html = self._wrap_in_template(html_content, source_file.stem)

            with open(output_file, "w") as f:
                f.write(full_html)

        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error converting {source_file}: {e}")

    def _wrap_in_template(self, content: str, title: str) -> str:
        """Wrap content in HTML template."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - PAKE System Documentation</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 2em;
            margin-bottom: 1em;
        }}
        h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        code {{
            background-color: #f1f2f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        }}
        pre {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 0;
            padding: 10px 20px;
            background-color: #f8f9fa;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .nav {{
            background: #2c3e50;
            color: white;
            padding: 10px 0;
            margin: -20px -20px 20px -20px;
            border-radius: 8px 8px 0 0;
        }}
        .nav a {{
            color: white;
            text-decoration: none;
            margin: 0 15px;
        }}
        .nav a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="index.html">Home</a>
            <a href="architecture/index.html">Architecture</a>
            <a href="api/index.html">API Reference</a>
            <a href="user_guide/index.html">User Guide</a>
            <a href="development/index.html">Development</a>
        </div>
        {content}
    </div>
</body>
</html>
"""

    def _generate_index(self) -> None:
        """Generate main index page."""
        index_content = """
# PAKE System Documentation

Welcome to the comprehensive documentation for the PAKE System, an enterprise-grade knowledge management and AI research platform.

## Quick Start

- [Installation Guide](user_guide/index.html) - Get started with PAKE System
- [API Reference](api/index.html) - Complete API documentation
- [Architecture Overview](architecture/index.html) - System architecture and design
- [Development Guide](development/index.html) - Contributing to PAKE System

## Key Features

- **Multi-Source Data Ingestion**: Seamlessly integrate data from various sources
- **AI-Powered Analytics**: Advanced machine learning for trend detection and insights
- **Real-Time Processing**: Live data processing with WebSocket support
- **Enterprise Security**: Comprehensive security features and compliance
- **Scalable Architecture**: Built for high-performance and scalability

## Documentation Sections

### Architecture
Comprehensive documentation of the PAKE System architecture, including:
- Core architecture components
- Service architecture and design patterns
- Data architecture and storage
- Security architecture and implementation
- Deployment architecture and strategies
- Monitoring and observability

### API Reference
Complete API documentation including:
- Authentication and authorization
- Data ingestion endpoints
- Analytics and intelligence endpoints
- Configuration management
- Monitoring and health checks
- Webhook integration

### User Guide
Everything you need to know to use the PAKE System effectively:
- Getting started and installation
- Data ingestion methods
- Analytics and trend detection
- Configuration and customization
- API usage and integration
- Troubleshooting and support

### Development Guide
Comprehensive guide for developers contributing to PAKE System:
- Development environment setup
- Coding standards and best practices
- Testing strategies and requirements
- Deployment procedures
- Contributing guidelines

## Support

For additional support and information:
- **Documentation**: This comprehensive guide
- **API Documentation**: Interactive API docs
- **Community Forum**: Developer community forums
- **Support Tickets**: Submit support tickets for assistance
- **Enterprise Support**: Contact enterprise support team

---

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # Write temporary markdown file
        temp_file = Path("temp_index.md")
        with open(temp_file, "w") as f:
            f.write(index_content)

        self._convert_markdown_to_html(temp_file, self.output_dir / "index.html")

        # Clean up temporary file
        temp_file.unlink(missing_ok=True)

    def _copy_static_files(self) -> None:
        """Copy static files to output directory."""
        static_dir = self.source_dir / "static"
        if static_dir.exists():
            import shutil

            shutil.copytree(static_dir, self.output_dir / "static", dirs_exist_ok=True)


def main():
    """Main function to build documentation."""
    builder = DocumentationBuilder()
    builder.build_documentation()


if __name__ == "__main__":
    main()
