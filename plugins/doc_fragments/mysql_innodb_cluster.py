# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ron Gershburg (@ronger4)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


class ModuleDocFragment(object):

    DOCUMENTATION = r'''
options:
  login_user:
    description:
      - The username used to authenticate with MySQL.
      - This user must have the necessary privileges for InnoDB Cluster administration.
    type: str
    required: true
  login_password:
    description:
      - The password used to authenticate with MySQL.
    type: str
    required: true
  login_host:
    description:
      - Host running the MySQL instance to connect to.
    type: str
    default: localhost
  login_port:
    description:
      - Port of the MySQL instance.
    type: int
    default: 3306
  login_unix_socket:
    description:
      - The path to a Unix domain socket for local connections.
      - When specified, overrides I(login_host) and I(login_port).
    type: str
  mysqlsh_path:
    description:
      - Path to the C(mysqlsh) binary.
      - If not specified, the module searches for C(mysqlsh) in the system PATH.
    type: path
  ca_cert:
    description:
      - The path to a Certificate Authority (CA) certificate for SSL connections.
      - "B(Not yet implemented.) Accepted for forward compatibility but currently ignored."
    type: path
    aliases: [ ssl_ca ]
  client_cert:
    description:
      - The path to a client public key certificate for SSL connections.
      - "B(Not yet implemented.) Accepted for forward compatibility but currently ignored."
    type: path
    aliases: [ ssl_cert ]
  client_key:
    description:
      - The path to the client private key for SSL connections.
      - "B(Not yet implemented.) Accepted for forward compatibility but currently ignored."
    type: path
    aliases: [ ssl_key ]
requirements:
   - MySQL Shell (mysqlsh) 8.0.13 or later installed on the controller or target host.
   - MySQL Server 8.0 or later (InnoDB Cluster is not available on MySQL 5.7 or MariaDB).
notes:
   - InnoDB Cluster requires a minimum of 3 MySQL instances for production deployments.
   - The connected MySQL user must have full administrative privileges
     (SUPER, GRANT OPTION, CREATE USER, RELOAD, etc.) or be a cluster admin
     account created by MySQL Shell.
   - MySQL Shell's C(--json=raw) output mode is used for machine-parseable responses.
   - All operations use the mysqlsh C(--) CLI integration syntax.
     No interactive prompts are issued.
attributes:
  check_mode:
    description: Can run in check_mode and return changed status prediction without modifying target.
  idempotent:
    description:
      - When run twice in a row outside check mode, with the same arguments, the second invocation indicates no change.
      - This assumes that the cluster has not changed between invocations.
'''
