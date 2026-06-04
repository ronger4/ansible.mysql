#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ron Gershburg (@ronger4)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: mysql_innodb_cluster_info
short_description: Gather information about a MySQL InnoDB Cluster
description:
  - Gathers status and configuration information about a MySQL InnoDB Cluster
    using the MySQL Shell AdminAPI.
  - Returns cluster status, member list, topology mode, and optionally
    cluster options and registered routers.
version_added: '5.1.0'

options:
  name:
    description:
      - Name of the InnoDB Cluster to query.
      - If omitted, the default cluster on the connected instance is used.
    type: str
  filter:
    description:
      - Limit the collected information by specifying a list of sections.
      - "Allowable values: C(status), C(members), C(options), C(routers), C(topology)."
      - By default, all sections are returned.
    type: list
    elements: str
  extended:
    description:
      - Level of detail for the cluster status output.
      - Maps directly to the C(extended) option of C(cluster.status()).
      - "C(0) - regular output (default)."
      - "C(1) - includes additional info about transactions."
      - "C(2) - includes detailed replication info."
      - "C(3) - includes full transaction set info."
    type: int
    default: 0
    choices: [0, 1, 2, 3]

attributes:
  check_mode:
    support: full
  idempotent:
    support: full

notes:
  - This module is read-only and never modifies cluster state.
  - Compatible only with MySQL 8.0+ (not MariaDB).

seealso:
  - module: ansible.mysql.mysql_innodb_cluster
  - module: ansible.mysql.mysql_info

author:
  - Ron Gershburg (@ronger4)

extends_documentation_fragment:
  - ansible.mysql.mysql_innodb_cluster
'''

EXAMPLES = r'''
- name: Get basic cluster status
  ansible.mysql.mysql_innodb_cluster_info:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
  register: cluster_info

- name: Get detailed cluster status with transaction info
  ansible.mysql.mysql_innodb_cluster_info:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    extended: 1
  register: cluster_info

- name: Get only members and topology info
  ansible.mysql.mysql_innodb_cluster_info:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    filter:
      - members
      - topology
  register: cluster_info

- name: Get cluster options
  ansible.mysql.mysql_innodb_cluster_info:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    filter:
      - options
  register: cluster_info

- name: Query a named cluster
  ansible.mysql.mysql_innodb_cluster_info:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    name: myProductionCluster
  register: cluster_info
'''

RETURN = r'''
cluster_name:
  description: Name of the InnoDB Cluster.
  returned: always
  type: str
  sample: "myCluster"
status:
  description: Overall cluster status.
  returned: always
  type: str
  sample: "OK"
topology_mode:
  description: Current topology mode of the cluster.
  returned: always
  type: str
  sample: "Single-Primary"
primary:
  description: Address of the current primary instance (single-primary mode).
  returned: when in single-primary mode
  type: str
  sample: "primary-db:3306"
members:
  description: List of cluster member details.
  returned: when not excluded by filter
  type: list
  elements: dict
  sample:
    - address: "primary-db:3306"
      role: "PRIMARY"
      state: "ONLINE"
      version: "8.0.38"
    - address: "replica1-db:3306"
      role: "SECONDARY"
      state: "ONLINE"
      version: "8.0.38"
group_name:
  description: The Group Replication group name (UUID).
  returned: always
  type: str
  sample: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
cluster_options:
  description: Cluster-level configuration options.
  returned: when 'options' is in filter
  type: dict
  sample: {"exitStateAction": "ABORT_SERVER", "memberWeight": "50"}
routers:
  description: List of registered MySQL Router instances.
  returned: when 'routers' is in filter
  type: list
  elements: dict
  sample:
    - hostname: "app-server-1"
      name: "app-server-1::system"
      last_check_in: "2026-01-15 10:30:00"
raw_status:
  description: Complete raw output from cluster.status() as returned by mysqlsh.
  returned: always
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.mysql.plugins.module_utils.mysqlsh import (
    find_mysqlsh,
    build_uri,
    run_mysqlsh,
    MysqlShellError,
)


def get_cluster_status(module, mysqlsh_path, uri, password, name, extended):
    """Retrieve cluster status via mysqlsh -- cluster status."""
    args = []
    if extended > 0:
        args.append(f'--extended={extended}')

    try:
        result = run_mysqlsh(module, mysqlsh_path, uri, password,
                             'cluster', 'status', args or None)
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to get cluster status: {e}")

    return result


def get_cluster_options(module, mysqlsh_path, uri, password):
    """Retrieve cluster options via mysqlsh -- cluster options."""
    try:
        result = run_mysqlsh(module, mysqlsh_path, uri, password,
                             'cluster', 'options')
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to get cluster options: {e}")

    return result


def extract_members(status_data):
    """Extract member list from cluster status output."""
    members = []
    default_set = status_data.get('defaultReplicaSet', {})
    topology = default_set.get('topology', {})

    for address, member_info in topology.items():
        members.append({
            'address': address,
            'role': member_info.get('memberRole', member_info.get('role', 'UNKNOWN')),
            'state': member_info.get('status', 'UNKNOWN'),
            'mode': member_info.get('mode', 'UNKNOWN'),
            'version': member_info.get('version', 'UNKNOWN'),
        })

    return members


def extract_primary(status_data):
    """Extract the primary instance address from cluster status."""
    default_set = status_data.get('defaultReplicaSet', {})
    topology = default_set.get('topology', {})

    for address, member_info in topology.items():
        role = member_info.get('memberRole', member_info.get('role', ''))
        if role.upper() == 'PRIMARY':
            return address

    return None


def extract_routers(status_data):
    """Extract registered routers from cluster status (if present)."""
    routers_raw = status_data.get('routers', {})
    routers = []
    for name, info in routers_raw.items():
        routers.append({
            'name': name,
            'hostname': info.get('hostname', ''),
            'last_check_in': info.get('lastCheckIn', ''),
            'version': info.get('version', ''),
        })
    return routers


def main():
    argument_spec = dict(
        login_user=dict(type='str', required=True),
        login_password=dict(type='str', required=True, no_log=True),
        login_host=dict(type='str', default='localhost'),
        login_port=dict(type='int', default=3306),
        login_unix_socket=dict(type='str'),
        mysqlsh_path=dict(type='path'),
        ca_cert=dict(type='path', aliases=['ssl_ca']),
        client_cert=dict(type='path', aliases=['ssl_cert']),
        client_key=dict(type='path', aliases=['ssl_key']),
        name=dict(type='str'),
        filter=dict(type='list', elements='str'),
        extended=dict(type='int', default=0, choices=[0, 1, 2, 3]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    login_user = module.params['login_user']
    login_password = module.params['login_password']
    login_host = module.params['login_host']
    login_port = module.params['login_port']
    login_unix_socket = module.params['login_unix_socket']
    mysqlsh_path_param = module.params['mysqlsh_path']
    name = module.params['name']
    filter_ = module.params['filter']
    extended = module.params['extended']

    mysqlsh_path = find_mysqlsh(module, mysqlsh_path_param)
    uri, password = build_uri(login_user, login_password, login_host,
                              login_port, login_unix_socket)

    status_data = get_cluster_status(module, mysqlsh_path, uri, password,
                                     name, extended)

    if status_data is None:
        module.fail_json(msg="No status data returned from cluster")

    result = {
        'changed': False,
        'cluster_name': status_data.get('clusterName', ''),
        'status': status_data.get('defaultReplicaSet', {}).get('status', ''),
        'topology_mode': status_data.get('defaultReplicaSet', {}).get(
            'topologyMode', ''),
        'group_name': status_data.get('defaultReplicaSet', {}).get(
            'groupName', ''),
        'primary': extract_primary(status_data),
        'raw_status': status_data,
    }

    should_include_all = filter_ is None

    if should_include_all or 'members' in filter_:
        result['members'] = extract_members(status_data)

    if should_include_all or 'topology' in filter_:
        result['topology_mode'] = status_data.get(
            'defaultReplicaSet', {}).get('topologyMode', '')

    if should_include_all or 'routers' in filter_:
        result['routers'] = extract_routers(status_data)

    if should_include_all or 'options' in filter_:
        options_data = get_cluster_options(module, mysqlsh_path, uri, password)
        result['cluster_options'] = options_data

    module.exit_json(**result)


if __name__ == '__main__':
    main()
