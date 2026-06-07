# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ron Gershburg (ronger4@gmail.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json


class MysqlShellError(Exception):
    """Raised when a mysqlsh CLI invocation fails."""

    def __init__(self, msg, rc=None, stdout=None, stderr=None):
        super(MysqlShellError, self).__init__(msg)
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr


def find_mysqlsh(module, mysqlsh_path=None):
    """Locate the mysqlsh binary.

    Args:
        module: AnsibleModule instance.
        mysqlsh_path: Explicit path provided by the user, or None for auto-detect.

    Returns:
        str: Absolute path to the mysqlsh binary.

    Raises:
        SystemExit via module.fail_json if the binary cannot be found.
    """
    if mysqlsh_path:
        return mysqlsh_path

    path = module.get_bin_path('mysqlsh', required=True)
    return path


def build_uri(user, password, host, port, socket=None, ssl_opts=None):
    """Build a mysqlsh connection URI string.

    Args:
        user: MySQL username.
        password: MySQL password.
        host: MySQL host.
        port: MySQL port.
        socket: Unix socket path (overrides host/port when set).
        ssl_opts: Dict with optional keys: ca_cert, client_cert, client_key.

    Returns:
        tuple: (uri_string, password) where password is passed separately
               to avoid embedding it in the URI.
    """
    if socket:
        uri = f"{user}@localhost?socket={socket}"
    else:
        uri = f"{user}@{host}:{port}"

    return uri, password


def run_mysqlsh(module, mysqlsh_path, uri, password, shell_object, method,
                args=None):
    """Execute a single AdminAPI call via mysqlsh -- CLI integration.

    Uses the mysqlsh command-line integration syntax:
        mysqlsh <uri> --password=<pass> --json=raw -- <object> <method> [args]

    Args:
        module: AnsibleModule instance (for run_command).
        mysqlsh_path: Path to the mysqlsh binary.
        uri: Connection URI (user@host:port).
        password: MySQL password (passed via --password=).
        shell_object: AdminAPI object (e.g., 'dba', 'cluster').
        method: Method to call in kebab-case (e.g., 'create-cluster', 'status').
        args: Optional list of positional/named arguments for the method.

    Returns:
        dict or None: Parsed JSON output from mysqlsh, or None if no output.

    Raises:
        MysqlShellError: If the command returns a non-zero exit code or
                         produces unparseable output.
    """
    cmd = [mysqlsh_path, uri, '--json=raw', '--no-wizard']

    if password:
        cmd.append(f'--password={password}')
    else:
        cmd.append('--no-password')

    cmd.extend(['--', shell_object, method])

    if args:
        cmd.extend(args)

    rc, stdout, stderr = module.run_command(cmd, cwd='/tmp')

    return parse_json_output(stdout, stderr, rc)


def run_mysqlsh_script(module, mysqlsh_path, uri, password, script):
    """Execute a Python script via mysqlsh --py -e for operations not in CLI mode.

    Used for cluster methods not available via -- CLI integration
    (e.g., switchToMultiPrimaryMode, switchToSinglePrimaryMode).

    Args:
        module: AnsibleModule instance.
        mysqlsh_path: Path to the mysqlsh binary.
        uri: Connection URI (user@host:port).
        password: MySQL password.
        script: Python script string to execute.

    Returns:
        dict or None: Parsed JSON output.

    Raises:
        MysqlShellError: On failure.
    """
    cmd = [mysqlsh_path, uri, '--json=raw', '--no-wizard', '--py']

    if password:
        cmd.append(f'--password={password}')
    else:
        cmd.append('--no-password')

    cmd.extend(['-e', script])

    rc, stdout, stderr = module.run_command(cmd, cwd='/tmp')

    return parse_json_output(stdout, stderr, rc)


def _parse_jsonl(text):
    """Parse JSONL (newline-delimited JSON) into a list of dicts.

    Skips empty lines and lines that aren't valid JSON.
    """
    objects = []
    if not text or not text.strip():
        return objects
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                objects.append(obj)
        except (ValueError, TypeError):
            continue
    return objects


def parse_json_output(stdout, stderr, rc):
    """Parse JSON output from mysqlsh --json=raw.

    mysqlsh with --json=raw outputs multiple JSON objects (one per line).
    Info/warning messages are separate objects with 'info' or 'warning' keys.
    The actual result is typically an object without those keys.

    Args:
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        rc: Return code from the command.

    Returns:
        dict or None: Parsed JSON result on success.

    Raises:
        MysqlShellError: On non-zero return code or JSON parse failure.
    """
    output = stdout.strip() if stdout else ''

    if rc != 0:
        error_msg = _extract_error_message(stdout, stderr, rc)
        raise MysqlShellError(error_msg, rc=rc, stdout=stdout, stderr=stderr)

    if not output:
        return None

    try:
        return json.loads(output)
    except (ValueError, TypeError):
        pass

    metadata_keys = {'info', 'warning', 'note', 'error'}
    parsed_lines = _parse_jsonl(output)
    for obj in parsed_lines:
        if set(obj.keys()) - metadata_keys:
            return obj

    if parsed_lines:
        return None

    raise MysqlShellError(f"Failed to parse mysqlsh JSON output: {output}",
                          rc=rc, stdout=stdout, stderr=stderr)


def _extract_error_message(stdout, stderr, rc):
    """Extract a human-readable error from mysqlsh JSONL output.

    Parses each line looking for error objects. Falls back to raw text.
    """
    errors = []
    for text in (stdout, stderr):
        for obj in _parse_jsonl(text):
            if 'error' in obj:
                err = obj['error']
                if isinstance(err, dict):
                    errors.append(err.get('message', str(err)))
                else:
                    errors.append(str(err).strip())
            elif 'message' in obj:
                errors.append(obj['message'].strip())

    if errors:
        return ' '.join(errors)

    if stderr and stderr.strip():
        return stderr.strip()
    if stdout and stdout.strip():
        return stdout.strip()

    return f"mysqlsh command failed with exit code {rc}"
