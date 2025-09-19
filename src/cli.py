from __future__ import annotations
from pathlib import Path
from typing import Optional
import json
import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

from .db import init_db
from .services import (
    create_note, list_notes, get_note, edit_note,
    delete_note, pin_note, archive_note, restore_note, purge_note,
    extract_links, backlinks_for,  # already in your services
    # search_notes_fts is optional; uncomment if you added FTS
    # search_notes_fts,
)

app = typer.Typer(help="Notely — simple note CLI")
console = Console()

@app.callback()
def _boot():
    init_db()

@app.command()
def add(
    title: str = typer.Option(..., "--title", "-t"),
    content: str = typer.Option("", "--content", "-c"),
    tags: Optional[str] = typer.Option(None, "--tags", "-g", help="comma separated"),
):
    n = create_note(title, content, (tags or "").split(","))
    console.print(f"[green]Created[/] #{n.id}: {n.title}")

@app.command("list")
def _list(
    tag: Optional[str] = typer.Option(None, "--tag"),
    search: Optional[str] = typer.Option(None, "--search"),
    archived: bool = typer.Option(False, "--archived"),
    sort: str = typer.Option("updated", "--sort", help="updated|created|title"),
):
    notes = list_notes(tag=tag, search=search, include_archived=archived, sort=sort)
    table = Table(title="Notely")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Tags", style="magenta")
    table.add_column("Pinned")
    table.add_column("Archived")
    table.add_column("Updated")
    for n in notes:
        table.add_row(
            str(n.id), n.title, ", ".join(n.tags),
            "✓" if n.pinned else "", "✓" if n.archived else "",
            n.updated_at.isoformat(timespec="minutes"),
        )
    console.print(table)

@app.command()
def show(identifier: str):
    n = get_note(identifier)
    if not n:
        console.print(f"[red]Not found[/]: {identifier}")
        raise typer.Exit(1)
    console.rule(f"#{n.id} {n.title}")
    if n.tags:
        console.print(f"[dim]tags:[/] {', '.join(n.tags)}")
    console.print(Markdown(n.content or "_<empty>_"))
    links = extract_links(n.content)
    if links:
        console.print(f"[dim]links:[/] {', '.join(links)}")
    bl = backlinks_for(identifier)
    if bl:
        console.print("[dim]backlinks from:[/]")
        for b in bl:
            console.print(f"  - #{b.id} {b.title}")

@app.command()
def edit(
    identifier: str,
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    content: Optional[str] = typer.Option(None, "--content", "-c"),
    tags: Optional[str] = typer.Option(None, "--tags", "-g"),
    pin: Optional[bool] = typer.Option(None, "--pin/--no-pin"),
    archive: Optional[bool] = typer.Option(None, "--archive/--unarchive"),
):
    n = edit_note(
        identifier,
        title=title,
        content=content,
        tags=(None if tags is None else tags.split(",")),
        pinned=pin,
        archived=archive,
    )
    console.print(f"[green]Updated[/] #{n.id}: {n.title}")

@app.command()
def delete(identifier: str, hard: bool = typer.Option(False, "--hard")):
    delete_note(identifier, hard=hard)
    console.print("[yellow]Deleted[/] (soft by default)")

@app.command()
def pin(identifier: str):
    n = pin_note(identifier, True)
    console.print(f"[green]Pinned[/] #{n.id}: {n.title}")

@app.command()
def unpin(identifier: str):
    n = pin_note(identifier, False)
    console.print(f"[yellow]Unpinned[/] #{n.id}: {n.title}")

@app.command()
def archive(identifier: str):
    n = archive_note(identifier, True)
    console.print(f"[yellow]Archived[/] #{n.id}: {n.title}")

@app.command()
def unarchive(identifier: str):
    n = archive_note(identifier, False)
    console.print(f"[green]Unarchived[/] #{n.id}: {n.title}")

@app.command()
def restore(identifier: str):
    n = restore_note(identifier)
    console.print(f"[green]Restored[/] #{n.id}: {n.title}")

@app.command()
def purge(identifier: str):
    purge_note(identifier)
    console.print(f"[red]Purged[/]: {identifier}")

@app.command()
def export(to: Path = typer.Option(..., "--to")):
    notes = list_notes(include_archived=True)
    payload = [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "tags": n.tags,
            "pinned": n.pinned,
            "archived": n.archived,
            "created_at": n.created_at.isoformat(),
            "updated_at": n.updated_at.isoformat(),
        }
        for n in notes
    ]
    to.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"[green]Exported[/] {len(payload)} notes → {to}")

@app.command()
def import_(from_: Path = typer.Option(..., "--from")):
    data = json.loads(from_.read_text(encoding="utf-8"))
    for item in data:
        create_note(item["title"], item.get("content", ""), item.get("tags", []))
    console.print(f"[green]Imported[/] {len(data)} notes")

def main():
    app()

if __name__ == "__main__":
    main()
