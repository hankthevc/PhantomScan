"""Casefile generation for investigation."""

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

console = Console()


def generate_casefile(
    pkg_data: dict,
    date_str: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Generate investigation casefile for a package.

    Args:
        pkg_data: Package data dictionary (from feed JSON)
        date_str: Date string for context
        output_dir: Output directory (default: data/feeds/{date})

    Returns:
        Path to generated casefile
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if output_dir is None:
        output_dir = Path("data/feeds") / date_str

    output_dir.mkdir(parents=True, exist_ok=True)

    # Render casefile
    template_dir = Path("radar/reports/templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("casefile.md.j2")

    markdown = template.render(
        pkg=pkg_data,
        date=date_str,
        now=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    # Save casefile
    filename = f"case_{pkg_data['ecosystem']}_{pkg_data['name']}.md"
    output_path = output_dir / filename
    output_path.write_text(markdown)

    console.print(f"[green]✓ Generated casefile: {output_path}[/green]")
    return output_path
