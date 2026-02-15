"""
Product Test BIT Client - Terminal CLI with Rich UI
Runs on Test PC and communicates with Jetson server.
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.api_client import APIClient
from common.models import TestRun, CheckStatus
from common.constants import (
    COLOR_PASSED, COLOR_FAILED, COLOR_WARNING, COLOR_SKIPPED, COLOR_RUNNING,
    SYMBOL_PASSED, SYMBOL_FAILED, SYMBOL_WARNING, SYMBOL_SKIPPED, SYMBOL_RUNNING
)

console = Console()


def load_config():
    """Load client configuration"""
    config_path = os.path.join(os.path.dirname(__file__), 'client_config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"[red]✗ Configuration file not found: {config_path}[/red]")
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Error parsing config file: {e}[/red]")
        sys.exit(1)


def get_status_symbol_and_color(status):
    """Get symbol and color for a check status"""
    status_map = {
        CheckStatus.PASSED.value: (SYMBOL_PASSED, COLOR_PASSED),
        CheckStatus.FAILED.value: (SYMBOL_FAILED, COLOR_FAILED),
        CheckStatus.WARNING.value: (SYMBOL_WARNING, COLOR_WARNING),
        CheckStatus.SKIPPED.value: (SYMBOL_SKIPPED, COLOR_SKIPPED),
        CheckStatus.RUNNING.value: (SYMBOL_RUNNING, COLOR_RUNNING),
    }
    return status_map.get(status, ("?", "white"))


def create_results_table(test_run_dict):
    """Create a rich table from test results"""
    table = Table(title="Test Results", show_header=True, header_style="bold cyan")

    table.add_column("Status", style="bold", width=8)
    table.add_column("Category", width=12)
    table.add_column("Check", width=30)
    table.add_column("Message", width=50)
    table.add_column("Duration", justify="right", width=10)

    for result in test_run_dict.get('results', []):
        symbol, color = get_status_symbol_and_color(result['status'])
        status_text = Text(f"{symbol} {result['status']}", style=color)

        table.add_row(
            status_text,
            result.get('category', 'unknown'),
            result.get('name', 'Unknown'),
            result.get('message', '')[:50],  # Truncate long messages
            f"{result.get('duration', 0):.2f}s"
        )

    return table


def create_summary_panel(summary):
    """Create a summary panel"""
    total = summary.get('total', 0)
    passed = summary.get('passed', 0)
    failed = summary.get('failed', 0)
    warnings = summary.get('warnings', 0)
    skipped = summary.get('skipped', 0)

    summary_text = f"""
[green]✓ Passed:[/green]   {passed}/{total}
[red]✗ Failed:[/red]   {failed}/{total}
[yellow]⚠ Warnings:[/yellow] {warnings}/{total}
[blue]○ Skipped:[/blue]  {skipped}/{total}
    """

    # Determine overall status
    if failed > 0:
        title_color = "red"
        title = "TEST FAILED"
    elif warnings > 0:
        title_color = "yellow"
        title = "TEST PASSED (with warnings)"
    else:
        title_color = "green"
        title = "TEST PASSED"

    return Panel(summary_text.strip(), title=f"[{title_color}]{title}[/{title_color}]", border_style=title_color)


def run_tests_command(client, category=None):
    """Run tests and display results"""
    console.print("\n[cyan]Starting test run...[/cyan]")

    try:
        # Start tests
        response = client.run_tests(category=category)
        test_id = response.get('test_id')

        if not test_id:
            console.print("[red]✗ Failed to start test[/red]")
            return 1

        console.print(f"[green]✓ Test started (ID: {test_id})[/green]\n")

        # Poll for results with live updates
        with Live(console=console, refresh_per_second=2) as live:
            while True:
                try:
                    results = client.get_results(test_id)
                    status = results.get('status')

                    # Create progress display
                    table = create_results_table(results)
                    live.update(table)

                    # Check if completed
                    if status == 'completed':
                        break

                    time.sleep(1)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Test interrupted by user[/yellow]")
                    return 1
                except Exception as e:
                    console.print(f"\n[red]Error polling results: {e}[/red]")
                    return 1

        # Display final results
        console.print()
        results = client.get_results(test_id)
        summary_panel = create_summary_panel(results.get('summary', {}))
        console.print(summary_panel)

        # Return exit code
        failed = results.get('summary', {}).get('failed', 0)
        return 1 if failed > 0 else 0

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return 1


def status_command(client):
    """Show server status"""
    try:
        status = client.get_status()
        system_info = client.get_system_info()

        table = Table(title="Server Status", show_header=False)
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Value", style="white")

        table.add_row("Status", "[green]" + status.get('status', 'unknown') + "[/green]")
        table.add_row("Hostname", system_info.get('hostname', 'unknown'))
        table.add_row("Platform", system_info.get('os_version', 'unknown'))
        table.add_row("CPU Cores", str(system_info.get('cpu_count', '?')))
        table.add_row("Total RAM", f"{system_info.get('total_ram_gb', 0):.2f} GB")
        table.add_row("Total Disk", f"{system_info.get('total_disk_gb', 0):.2f} GB")

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return 1


def results_command(client):
    """Show latest test results"""
    try:
        results = client.get_results()

        if 'error' in results:
            console.print(f"[yellow]No test results available[/yellow]")
            return 0

        table = create_results_table(results)
        console.print(table)

        summary_panel = create_summary_panel(results.get('summary', {}))
        console.print("\n")
        console.print(summary_panel)

        return 0

    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Product Test BIT Client")
    parser.add_argument('command', choices=['run', 'status', 'results', 'export-params', 'compare-params'],
                        help='Command to execute')
    parser.add_argument('category', nargs='?', help='Test category (for run command)')

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    # Create API client
    jetson_config = config.get('jetson', {})
    base_url = f"http://{jetson_config.get('ip')}:{jetson_config.get('port')}"
    client = APIClient(base_url, timeout=jetson_config.get('timeout', 60))

    # Print banner
    console.print("\n" + "="*60)
    console.print("[bold cyan]Product Test BIT Client[/bold cyan]".center(60))
    console.print("="*60 + "\n")

    # Check server connectivity
    console.print(f"Connecting to server at [cyan]{base_url}[/cyan]...", end=" ")
    if not client.ping():
        console.print("[red]✗ FAILED[/red]")
        console.print(f"\n[red]Cannot connect to server at {base_url}[/red]")
        console.print("[yellow]Please check:[/yellow]")
        console.print("  1. Server is running on Jetson")
        console.print("  2. Network connection is active")
        console.print(f"  3. IP address in client_config.json is correct ({jetson_config.get('ip')})")
        return 1

    console.print("[green]✓ Connected[/green]\n")

    # Execute command
    if args.command == 'run':
        return run_tests_command(client, args.category)
    elif args.command == 'status':
        return status_command(client)
    elif args.command == 'results':
        return results_command(client)
    elif args.command == 'export-params':
        try:
            result = client.export_params()
            console.print(result)
            return 0
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            return 1
    elif args.command == 'compare-params':
        try:
            result = client.compare_params()
            console.print(result)
            return 0
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
