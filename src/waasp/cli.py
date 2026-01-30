"""WAASP Command Line Interface."""

import click
from flask.cli import with_appcontext

from waasp.models import db, Contact, TrustLevel
from waasp.services import WhitelistService


@click.group()
def main():
    """WAASP - Security whitelist for agentic AI."""
    pass


@main.command()
@click.argument("sender_id")
@click.option("--channel", "-c", help="Channel scope (whatsapp, telegram, etc.)")
def check(sender_id: str, channel: str | None):
    """Check if a sender is allowed."""
    from waasp.app import create_app
    
    app = create_app()
    with app.app_context():
        service = WhitelistService()
        result = service.check(sender_id, channel)
        
        if result.allowed:
            click.secho(f"✓ ALLOWED ({result.trust_level.value})", fg="green")
        else:
            click.secho(f"✗ BLOCKED", fg="red")
        
        if result.contact and result.contact.name:
            click.echo(f"  Name: {result.contact.name}")
        click.echo(f"  Reason: {result.reason}")


@main.command()
@click.argument("sender_id")
@click.option("--name", "-n", help="Human-readable name")
@click.option("--trust", "-t", 
              type=click.Choice(["sovereign", "trusted", "limited", "blocked"]),
              default="trusted",
              help="Trust level")
@click.option("--channel", "-c", help="Channel scope")
def add(sender_id: str, name: str | None, trust: str, channel: str | None):
    """Add a contact to the whitelist."""
    from waasp.app import create_app
    
    app = create_app()
    with app.app_context():
        service = WhitelistService()
        
        try:
            contact = service.add_contact(
                sender_id=sender_id,
                name=name,
                trust_level=TrustLevel(trust),
                channel=channel,
            )
            click.secho(f"✓ Added {contact.sender_id} ({contact.trust_level.value})", fg="green")
        except ValueError as e:
            click.secho(f"✗ {e}", fg="red")
            raise SystemExit(1)


@main.command("list")
@click.option("--trust", "-t",
              type=click.Choice(["sovereign", "trusted", "limited", "blocked"]),
              help="Filter by trust level")
@click.option("--channel", "-c", help="Filter by channel")
def list_contacts(trust: str | None, channel: str | None):
    """List all contacts."""
    from waasp.app import create_app
    
    app = create_app()
    with app.app_context():
        service = WhitelistService()
        
        trust_level = TrustLevel(trust) if trust else None
        contacts = service.list_contacts(trust_level=trust_level, channel=channel)
        
        if not contacts:
            click.echo("No contacts found.")
            return
        
        for contact in contacts:
            color = {
                TrustLevel.SOVEREIGN: "cyan",
                TrustLevel.TRUSTED: "green",
                TrustLevel.LIMITED: "yellow",
                TrustLevel.BLOCKED: "red",
            }.get(contact.trust_level, "white")
            
            name = contact.name or "(no name)"
            channel_str = f"[{contact.channel}]" if contact.channel else "[global]"
            
            click.secho(
                f"  {contact.trust_level.value:10} {channel_str:12} {contact.sender_id:20} {name}",
                fg=color,
            )


@main.command()
@click.argument("sender_id")
@click.option("--channel", "-c", help="Channel scope")
def remove(sender_id: str, channel: str | None):
    """Remove a contact from the whitelist."""
    from waasp.app import create_app
    
    app = create_app()
    with app.app_context():
        service = WhitelistService()
        
        if service.remove_contact(sender_id, channel):
            click.secho(f"✓ Removed {sender_id}", fg="green")
        else:
            click.secho(f"✗ Contact not found", fg="red")
            raise SystemExit(1)


@main.command()
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind")
@click.option("--port", "-p", default=8000, help="Port to bind")
def serve(host: str, port: int):
    """Start the API server."""
    from waasp.app import create_app
    
    app = create_app()
    click.echo(f"Starting WAASP API on {host}:{port}")
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
