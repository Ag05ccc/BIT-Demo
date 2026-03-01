"""
Product Test BIT Client - Terminal CLI
Runs on Test PC and communicates with Jetson server.
Uses only Python stdlib — no external dependencies.
"""

import sys
import os
import json
import time
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.api_client import APIClient
from common.models import CheckStatus
from common.constants import (
    SYMBOL_PASSED, SYMBOL_FAILED, SYMBOL_WARNING, SYMBOL_SKIPPED, SYMBOL_RUNNING
)

# ---------------------------------------------------------------------------
# ANSI terminal colours — no external dependency required
# ---------------------------------------------------------------------------
_R      = "\033[0m"   # reset
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_GREEN  = "\033[32m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_BLUE   = "\033[34m"
_CYAN   = "\033[36m"

_STATUS_ANSI = {
    'passed':  _GREEN,
    'failed':  _RED,
    'warning': _YELLOW,
    'skipped': _BLUE,
    'running': _CYAN,
}

def _c(ansi, text):
    """Wrap text in an ANSI colour sequence."""
    return f"{ansi}{text}{_R}"

# ---------------------------------------------------------------------------
# Table layout — column widths (characters)
# ---------------------------------------------------------------------------
_W_STATUS = 14
_W_CAT    = 13
_W_CHECK  = 31
_W_MSG    = 51
_W_SOURCE = 46
_W_DUR    =  9

def _col(text, width):
    """Truncate and left-pad a string to exactly `width` visible chars."""
    return str(text)[:width].ljust(width)

def _table_width(has_source):
    w = _W_STATUS + _W_CAT + _W_CHECK + _W_MSG + _W_DUR
    return w + _W_SOURCE if has_source else w

def _rule(width, color=_DIM):
    print(_c(color, "─" * width))

def _section_rule(title, width, color=_CYAN):
    """Print a labelled horizontal divider:  ─── title ───"""
    if title:
        side = max(0, (width - len(title) - 2) // 2)
        rest = width - len(title) - 2 - side
        print(color + "─" * side + f" {title} " + "─" * rest + _R)
    else:
        _rule(width, color)

def _panel(body_text, title="", color=_DIM):
    """Draw a simple bordered panel around multi-line text."""
    lines = body_text.split('\n')
    inner = max((len(ln) for ln in lines), default=0) + 2
    inner = max(inner, len(title) + 6, 24)
    _section_rule(title, inner, color)
    for ln in lines:
        print(f" {ln}")
    print(_c(color, "─" * inner))

# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------
def get_status_symbol_and_color(status):
    """Return (unicode symbol, ANSI colour code) for a check status."""
    sym = {
        CheckStatus.PASSED.value:  SYMBOL_PASSED,
        CheckStatus.FAILED.value:  SYMBOL_FAILED,
        CheckStatus.WARNING.value: SYMBOL_WARNING,
        CheckStatus.SKIPPED.value: SYMBOL_SKIPPED,
        CheckStatus.RUNNING.value: SYMBOL_RUNNING,
    }.get(status, "?")
    ansi = _STATUS_ANSI.get(status, "")
    return sym, ansi

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------
def load_config(config_path=None):
    """Load client configuration from JSON."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'client_config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(_c(_RED, f"\u2717 Configuration file not found: {config_path}"))
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(_c(_RED, f"\u2717 Error parsing config file: {e}"))
        sys.exit(1)

# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------
def _print_table_header(has_source):
    w = _table_width(has_source)
    header = (
        _BOLD + _CYAN +
        _col("Status",   _W_STATUS) +
        _col("Category", _W_CAT)   +
        _col("Check",    _W_CHECK)  +
        _col("Message",  _W_MSG)    +
        (_col("Source Location", _W_SOURCE) if has_source else "") +
        "Duration".rjust(_W_DUR) +
        _R
    )
    print(header)
    _rule(w)

def _print_result_row(result, has_source=False):
    symbol, ansi = get_status_symbol_and_color(result['status'])
    status_plain = f"{symbol} {result['status']}"
    source_loc   = result.get('details', {}).get('source_location', '')

    row = (
        _c(ansi,          _col(status_plain, _W_STATUS)) +
        _col(result.get('category', ''),          _W_CAT)   +
        _col(result.get('name',     ''),          _W_CHECK)  +
        _col(result.get('message',  '')[:50],     _W_MSG)
    )
    if has_source:
        row += _c(_DIM + _CYAN, _col(source_loc, _W_SOURCE))
    row += f"{result.get('duration', 0):>{_W_DUR}.2f}s"
    print(row)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary(summary):
    total    = summary.get('total',    0)
    passed   = summary.get('passed',   0)
    failed   = summary.get('failed',   0)
    warnings = summary.get('warnings', 0)
    skipped  = summary.get('skipped',  0)

    if failed > 0:
        title_ansi, title = _RED,    "TEST FAILED"
    elif warnings > 0:
        title_ansi, title = _YELLOW, "TEST PASSED (with warnings)"
    else:
        title_ansi, title = _GREEN,  "TEST PASSED"

    width = 40
    print()
    _section_rule(title, width, title_ansi)
    lbl_pass = "\u2713 Passed:"
    lbl_fail = "\u2717 Failed:"
    lbl_warn = "\u26a0 Warnings:"
    lbl_skip = "\u25cb Skipped:"
    print(f"  {_c(_GREEN,  lbl_pass)}   {passed}/{total}")
    print(f"  {_c(_RED,    lbl_fail)}   {failed}/{total}")
    print(f"  {_c(_YELLOW, lbl_warn)} {warnings}/{total}")
    print(f"  {_c(_BLUE,   lbl_skip)}  {skipped}/{total}")
    _rule(width, title_ansi)

# ---------------------------------------------------------------------------
# Solutions
# ---------------------------------------------------------------------------
def print_solutions(test_run_dict):
    """Print fix hints for failed / warning / skipped checks."""
    issues = [
        r for r in test_run_dict.get('results', [])
        if r.get('status') in ('failed', 'warning', 'skipped')
        and r.get('details', {}).get('solution')
    ]
    if not issues:
        return

    print()
    _section_rule("Suggested Solutions", 60, _CYAN)

    for result in issues:
        symbol, ansi = get_status_symbol_and_color(result['status'])
        name     = result.get('name',    'Unknown')
        message  = result.get('message', '')
        solution = result['details']['solution']

        print(f"\n{_c(ansi, symbol + ' ' + name)} - {message}")
        print(_c(_DIM, "  How to fix:"))
        for line in solution.strip().split('\n'):
            print(f"    {line}")

    _rule(60)

# ---------------------------------------------------------------------------
# Debug tracebacks
# ---------------------------------------------------------------------------
def print_debug_tracebacks(test_run_dict):
    """Print full tracebacks when server was started with --debug."""
    issues = [
        r for r in test_run_dict.get('results', [])
        if r.get('details', {}).get('traceback')
    ]
    if not issues:
        return

    print()
    _section_rule("Developer Debug \u2014 Full Tracebacks", 60, _RED)

    for result in issues:
        name    = result.get('name', 'Unknown')
        source  = result.get('details', {}).get('source_location', 'unknown location')
        tb_text = result['details']['traceback'].rstrip()
        symbol, ansi = get_status_symbol_and_color(result['status'])

        print(f"\n{_c(ansi, symbol + ' ' + name)}  "
              f"{_c(_DIM, 'source:')} {_c(_CYAN, source)}")
        _panel(tb_text, color=_DIM)

    _rule(60, _RED)

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def run_tests_command(client, category=None):
    """Run tests and stream each result row as it arrives."""
    print(f"\n{_c(_CYAN, 'Starting test run...')}")

    try:
        response = client.run_tests(category=category)
        test_id  = response.get('test_id')

        if not test_id:
            print(_c(_RED, "\u2717 Failed to start test"))
            return 1

        started_msg = _c(_GREEN, "\u2713 Test started")
        print(f"{started_msg} (ID: {test_id})\n")

        printed_count  = 0
        header_printed = False

        while True:
            try:
                results     = client.get_results(test_id)
                all_results = results.get('results', [])
                has_source  = any(
                    r.get('details', {}).get('source_location')
                    for r in all_results
                )

                if not header_printed and all_results:
                    _print_table_header(has_source)
                    header_printed = True

                # Print only newly arrived rows
                for r in all_results[printed_count:]:
                    _print_result_row(r, has_source)
                    printed_count += 1

                if results.get('status') == 'completed':
                    break

                time.sleep(1)

            except KeyboardInterrupt:
                print(f"\n{_c(_YELLOW, 'Test interrupted by user')}")
                return 1
            except Exception as e:
                print(f"\n{_c(_RED, f'Error polling results: {e}')}")
                return 1

        if header_printed:
            _rule(_table_width(has_source))

        # Fetch final results for summary/solutions (may already be complete)
        results = client.get_results(test_id)
        print_summary(results.get('summary', {}))
        print_solutions(results)
        print_debug_tracebacks(results)

        failed = results.get('summary', {}).get('failed', 0)
        return 1 if failed > 0 else 0

    except Exception as e:
        print(_c(_RED, f"\u2717 Error: {e}"))
        return 1


def status_command(client):
    """Show server and system status."""
    try:
        status      = client.get_status()
        system_info = client.get_system_info()

        _section_rule("Server Status", 44)
        rows = [
            ("Status",     _c(_GREEN, status.get('status', 'unknown'))),
            ("Hostname",   system_info.get('hostname',     'unknown')),
            ("Platform",   system_info.get('os_version',   'unknown')),
            ("CPU Cores",  str(system_info.get('cpu_count', '?'))),
            ("Total RAM",  f"{system_info.get('total_ram_gb',  0):.2f} GB"),
            ("Total Disk", f"{system_info.get('total_disk_gb', 0):.2f} GB"),
        ]
        for label, value in rows:
            label_padded = (label + ':').ljust(14)
            print(f"  {_c(_CYAN, label_padded)} {value}")
        _rule(44)
        return 0

    except Exception as e:
        print(_c(_RED, f"\u2717 Error: {e}"))
        return 1


def results_command(client):
    """Show latest test results."""
    try:
        results = client.get_results()

        if 'error' in results:
            print(_c(_YELLOW, "No test results available"))
            return 0

        all_results = results.get('results', [])
        has_source  = any(
            r.get('details', {}).get('source_location')
            for r in all_results
        )

        _print_table_header(has_source)
        for r in all_results:
            _print_result_row(r, has_source)
        _rule(_table_width(has_source))

        print_summary(results.get('summary', {}))
        print_solutions(results)
        print_debug_tracebacks(results)
        return 0

    except Exception as e:
        print(_c(_RED, f"\u2717 Error: {e}"))
        return 1

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def report_command(client):
    """Download the HTML test report from the server and save it locally."""
    # Fetch the current test_id for a meaningful filename
    filename = None
    try:
        meta = client.get_results()
        tid  = meta.get('test_id', '')
        if tid:
            filename = f"bit_report_{tid}.html"
    except Exception:
        pass

    if not filename:
        filename = f"bit_report_{time.strftime('%Y%m%d_%H%M%S')}.html"

    try:
        data = client.get_report()
        with open(filename, 'wb') as fh:
            fh.write(data)
        saved_msg = _c(_GREEN, "\u2713 Report saved:")
        print(f"{saved_msg} {filename}")
        return 0
    except Exception as e:
        print(_c(_RED, f"\u2717 Error: {e}"))
        return 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Product Test BIT Client")
    parser.add_argument(
        'command',
        choices=['run', 'status', 'results', 'export-params', 'compare-params', 'report'],
        help='Command to execute'
    )
    parser.add_argument('category', nargs='?', help='Test category (for run command)')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to client config file (default: client_config.json)')

    args   = parser.parse_args()
    config = load_config(args.config)

    jetson_cfg = config.get('jetson', {})
    base_url   = f"http://{jetson_cfg.get('ip')}:{jetson_cfg.get('port')}"
    client     = APIClient(base_url, timeout=jetson_cfg.get('timeout', 60))

    # Banner
    print(f"\n{'=' * 60}")
    print(_c(_BOLD + _CYAN, "Product Test BIT Client".center(60)))
    print('=' * 60 + "\n")

    # Connectivity check
    print(f"Connecting to server at {_c(_CYAN, base_url)}...", end=" ", flush=True)
    if not client.ping():
        print(_c(_RED, "\u2717 FAILED"))
        print(f"\n{_c(_RED, 'Cannot connect to server at ' + base_url)}")
        print(_c(_YELLOW, "Please check:"))
        print("  1. Server is running on Jetson")
        print("  2. Network connection is active")
        print(f"  3. IP in client_config.json matches the server ({jetson_cfg.get('ip')})")
        return 1

    print(_c(_GREEN, "\u2713 Connected") + "\n")

    if args.command == 'run':
        return run_tests_command(client, args.category)
    elif args.command == 'status':
        return status_command(client)
    elif args.command == 'results':
        return results_command(client)
    elif args.command == 'export-params':
        try:
            print(client.export_params())
            return 0
        except Exception as e:
            print(_c(_RED, f"\u2717 Error: {e}"))
            return 1
    elif args.command == 'compare-params':
        try:
            print(client.compare_params())
            return 0
        except Exception as e:
            print(_c(_RED, f"\u2717 Error: {e}"))
            return 1
    elif args.command == 'report':
        return report_command(client)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{_c(_YELLOW, 'Interrupted by user')}")
        sys.exit(1)
