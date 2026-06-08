#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ron Gershburg (@ronger4@gmail.com)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: mysql_innodb_cluster
short_description: Manage MySQL InnoDB Cluster lifecycle
description:
  - Manages the lifecycle of a MySQL InnoDB Cluster using the MySQL Shell AdminAPI.
  - Supports creating, dissolving, adding/removing instances, rejoining instances,
    switching topology modes, changing the primary, setting options, and rescanning.
version_added: '5.1.0'

options:
  mode:
    description:
      - Module operating mode. Selects which cluster operation to perform.
      - C(create) - Create a new InnoDB Cluster on the connected instance.
      - C(dissolve) - Destroy the cluster and remove all metadata.
      - C(add_instance) - Add an instance to the cluster.
      - C(remove_instance) - Remove an instance from the cluster.
      - C(rejoin_instance) - Rejoin a previously lost or removed instance.
      - C(set_primary) - Change which instance is the primary (single-primary mode only).
      - C(set_option) - Set a cluster-level configuration option.
      - C(rescan) - Rescan the cluster for topology changes. This is NOT idempotent and always reports changed.
      - C(switch_to_multi_primary) - Switch the cluster to multi-primary mode.
      - C(switch_to_single_primary) - Switch the cluster to single-primary mode.
    type: str
    required: true
    choices:
      - create
      - dissolve
      - add_instance
      - remove_instance
      - rejoin_instance
      - set_primary
      - set_option
      - rescan
      - switch_to_multi_primary
      - switch_to_single_primary
  name:
    description:
      - Name of the InnoDB Cluster.
      - Required when I(mode=create).
    type: str
  instance:
    description:
      - "Target instance URI in the format C(user@host:port)."
      - Required when I(mode) is C(add_instance), C(remove_instance),
        C(rejoin_instance), or C(set_primary).
    type: str
  topology_mode:
    description:
      - Topology mode for the cluster.
      - Used with I(mode=create).
    type: str
    choices: ['single-primary', 'multi-primary']
    default: single-primary
  recovery_method:
    description:
      - Recovery method for a joining instance.
      - Used with I(mode=add_instance).
      - C(auto) lets MySQL Shell decide the best method.
      - C(clone) forces a full clone of the primary.
      - C(incremental) uses incremental recovery from the binlog.
    type: str
    choices: ['auto', 'clone', 'incremental']
    default: auto
  option_name:
    description:
      - Cluster option key to set.
      - Required when I(mode=set_option).
    type: str
  option_value:
    description:
      - Cluster option value to set.
      - Required when I(mode=set_option).
    type: str
  force:
    description:
      - Force the operation without confirmations.
      - When used with I(mode=create), skips instance validation checks and configures the instance during cluster creation.
      - Used with I(mode=create), I(mode=dissolve), and I(mode=remove_instance).
    type: bool
    default: false
  wait_recovery:
    description:
      - Number of seconds to wait for recovery to complete when adding or
        rejoining an instance.
      - C(0) means do not wait.
    type: int
    default: 0

attributes:
  check_mode:
    support: full
  idempotent:
    support: partial
    details:
      - The module is not idempotent for O(mode=rescan) which always reports changed.

notes:
  - Compatible only with MySQL 8.0+ (not MariaDB).
  - The C(rescan) mode always reports changed because its outcome cannot be predicted.

seealso:
  - module: ansible.mysql.mysql_innodb_cluster_info
  - module: ansible.mysql.mysql_replication

author:
  - Ron Gershburg (@ronger4)

extends_documentation_fragment:
  - ansible.mysql.mysql_innodb_cluster
'''

EXAMPLES = r'''
- name: Create a new InnoDB Cluster
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: create
    name: myCluster

- name: Create a multi-primary cluster
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: create
    name: myCluster
    topology_mode: multi-primary

- name: Add an instance to the cluster
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: add_instance
    instance: clusteradmin@replica1-db:3306

- name: Add an instance using clone recovery
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: add_instance
    instance: clusteradmin@replica2-db:3306
    recovery_method: clone

- name: Remove an instance from the cluster
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: remove_instance
    instance: clusteradmin@replica2-db:3306

- name: Rejoin an instance after network recovery
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: rejoin_instance
    instance: clusteradmin@replica1-db:3306

- name: Switch primary to a specific instance
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: set_primary
    instance: clusteradmin@replica1-db:3306

- name: Set a cluster option
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: set_option
    option_name: exitStateAction
    option_value: ABORT_SERVER

- name: Switch to multi-primary mode
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: switch_to_multi_primary

- name: Dissolve a cluster
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: dissolve
    force: true

- name: Rescan the cluster
  ansible.mysql.mysql_innodb_cluster:
    login_user: clusteradmin
    login_password: secret
    login_host: primary-db.example.com
    mode: rescan
'''

RETURN = r'''
changed:
  description: Whether the cluster state was modified.
  returned: always
  type: bool
msg:
  description: Human-readable result message.
  returned: always
  type: str
  sample: "Cluster 'myCluster' created successfully"
cluster:
  description: Cluster status after the operation (when applicable).
  returned: on success for most modes
  type: dict
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.mysql.plugins.module_utils.mysqlsh import (
    find_mysqlsh,
    build_uri,
    run_mysqlsh,
    run_mysqlsh_script,
    MysqlShellError,
)


def cluster_exists(module, mysqlsh_path, uri, password):
    """Check if an InnoDB Cluster exists on the connected instance."""
    try:
        run_mysqlsh(module, mysqlsh_path, uri, password, 'cluster', 'status')
        return True
    except MysqlShellError:
        return False


def get_cluster_status(module, mysqlsh_path, uri, password):
    """Get current cluster status. Returns None if cluster doesn't exist."""
    try:
        return run_mysqlsh(module, mysqlsh_path, uri, password,
                           'cluster', 'status')
    except MysqlShellError:
        return None


def instance_in_cluster(status_data, instance):
    """Check if an instance is a member of the cluster.

    Returns the member state (ONLINE, RECOVERING, etc.) or None.
    """
    if not status_data:
        return None

    default_set = status_data.get('defaultReplicaSet', {})
    topology = default_set.get('topology', {})

    instance_normalized = instance.split('@')[-1] if '@' in instance else instance

    for address, member_info in topology.items():
        if address == instance_normalized or instance_normalized in address:
            return member_info.get('status', 'UNKNOWN')

    return None


def get_current_primary(status_data):
    """Get the address of the current primary from status data."""
    if not status_data:
        return None

    default_set = status_data.get('defaultReplicaSet', {})
    topology = default_set.get('topology', {})

    for address, member_info in topology.items():
        role = member_info.get('memberRole', member_info.get('role', ''))
        if role.upper() == 'PRIMARY':
            return address

    return None


def get_topology_mode(status_data):
    """Get the current topology mode from status data."""
    if not status_data:
        return None
    return status_data.get('defaultReplicaSet', {}).get('topologyMode', None)


def mode_create(module, mysqlsh_path, uri, password, params):
    """Handle mode=create."""
    name = params['name']
    topology_mode = params['topology_mode']
    force = params['force']

    if not name:
        module.fail_json(msg="Parameter 'name' is required for mode=create")

    if cluster_exists(module, mysqlsh_path, uri, password):
        module.exit_json(changed=False,
                         msg="Cluster already exists")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg=f"Would create cluster '{name}'")

    args = [name]
    if topology_mode == 'multi-primary':
        args.append('--multiPrimary=true')
    if force:
        args.append('--force=true')

    try:
        result = run_mysqlsh(module, mysqlsh_path, uri, password,
                             'dba', 'create-cluster', args)
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to create cluster '{name}': {e}")

    module.exit_json(changed=True,
                     msg=f"Cluster '{name}' created successfully",
                     cluster=result)


def mode_dissolve(module, mysqlsh_path, uri, password, params):
    """Handle mode=dissolve."""
    force = params['force']

    if not cluster_exists(module, mysqlsh_path, uri, password):
        module.exit_json(changed=False,
                         msg="No cluster exists to dissolve")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg="Would dissolve cluster")

    args = []
    if force:
        args.append('--force=true')

    try:
        run_mysqlsh(module, mysqlsh_path, uri, password,
                    'cluster', 'dissolve', args or None)
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to dissolve cluster: {e}")

    module.exit_json(changed=True, msg="Cluster dissolved successfully")


def mode_add_instance(module, mysqlsh_path, uri, password, params):
    """Handle mode=add_instance."""
    instance = params['instance']
    recovery_method = params['recovery_method']

    if not instance:
        module.fail_json(msg="Parameter 'instance' is required for mode=add_instance")

    status_data = get_cluster_status(module, mysqlsh_path, uri, password)
    member_state = instance_in_cluster(status_data, instance)

    if member_state and member_state.upper() == 'ONLINE':
        module.exit_json(changed=False,
                         msg=f"Instance '{instance}' is already a member and ONLINE")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg=f"Would add instance '{instance}' to cluster")

    args = [instance]
    if recovery_method != 'auto':
        args.append(f'--recoveryMethod={recovery_method}')

    try:
        result = run_mysqlsh(module, mysqlsh_path, uri, password,
                             'cluster', 'add-instance', args)
    except MysqlShellError as e:
        # Support idempotency for add_instance
        if 'already part of' in str(e).lower():
            module.exit_json(changed=False,
                             msg=f"Instance '{instance}' is already a member")
        module.fail_json(msg=f"Failed to add instance '{instance}': {e}")

    module.exit_json(changed=True,
                     msg=f"Instance '{instance}' added to cluster",
                     cluster=result)


def mode_remove_instance(module, mysqlsh_path, uri, password, params):
    """Handle mode=remove_instance."""
    instance = params['instance']
    force = params['force']

    if not instance:
        module.fail_json(msg="Parameter 'instance' is required for mode=remove_instance")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg=f"Would remove instance '{instance}' from cluster")

    args = [instance]
    if force:
        args.append('--force=true')

    try:
        run_mysqlsh(module, mysqlsh_path, uri, password,
                    'cluster', 'remove-instance', args)
    except MysqlShellError as e:
        if 'does not belong' in str(e).lower() or 'is not a member' in str(e).lower():
            module.exit_json(changed=False,
                             msg=f"Instance '{instance}' is not in the cluster")
        module.fail_json(msg=f"Failed to remove instance '{instance}': {e}")

    module.exit_json(changed=True,
                     msg=f"Instance '{instance}' removed from cluster")


def mode_rejoin_instance(module, mysqlsh_path, uri, password, params):
    """Handle mode=rejoin_instance."""
    instance = params['instance']

    if not instance:
        module.fail_json(msg="Parameter 'instance' is required for mode=rejoin_instance")

    status_data = get_cluster_status(module, mysqlsh_path, uri, password)
    member_state = instance_in_cluster(status_data, instance)

    if member_state and member_state.upper() == 'ONLINE':
        module.exit_json(changed=False,
                         msg=f"Instance '{instance}' is already ONLINE")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg=f"Would rejoin instance '{instance}'")

    try:
        run_mysqlsh(module, mysqlsh_path, uri, password,
                    'cluster', 'rejoin-instance', [instance])
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to rejoin instance '{instance}': {e}")

    module.exit_json(changed=True,
                     msg=f"Instance '{instance}' rejoined cluster")


def mode_set_primary(module, mysqlsh_path, uri, password, params):
    """Handle mode=set_primary."""
    instance = params['instance']

    if not instance:
        module.fail_json(msg="Parameter 'instance' is required for mode=set_primary")

    status_data = get_cluster_status(module, mysqlsh_path, uri, password)
    primary_before = get_current_primary(status_data)

    if module.check_mode:
        module.exit_json(changed=True,
                         msg=f"Would set '{instance}' as primary")

    try:
        run_mysqlsh(module, mysqlsh_path, uri, password,
                    'cluster', 'set-primary-instance', [instance])
    except MysqlShellError as e:
        if 'already the primary' in str(e).lower():
            module.exit_json(changed=False,
                             msg=f"Instance '{instance}' is already the primary")
        module.fail_json(msg=f"Failed to set primary to '{instance}': {e}")

    status_after = get_cluster_status(module, mysqlsh_path, uri, password)
    primary_after = get_current_primary(status_after)

    if primary_before == primary_after:
        module.exit_json(changed=False,
                         msg=f"Instance '{instance}' is already the primary")

    module.exit_json(changed=True,
                     msg=f"Primary changed to '{instance}'")


def mode_set_option(module, mysqlsh_path, uri, password, params):
    """Handle mode=set_option."""
    option_name = params['option_name']
    option_value = params['option_value']

    if not option_name or option_value is None:
        module.fail_json(
            msg="Parameters 'option_name' and 'option_value' are required for mode=set_option")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg=f"Would set option '{option_name}' to '{option_value}'")

    try:
        run_mysqlsh(module, mysqlsh_path, uri, password,
                    'cluster', 'set-option', [option_name, option_value])
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to set option '{option_name}': {e}")

    module.exit_json(changed=True,
                     msg=f"Option '{option_name}' set to '{option_value}'")


def mode_rescan(module, mysqlsh_path, uri, password, params):
    """Handle mode=rescan."""
    if module.check_mode:
        module.exit_json(changed=True, msg="Would rescan cluster")

    try:
        result = run_mysqlsh(module, mysqlsh_path, uri, password,
                             'cluster', 'rescan')
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to rescan cluster: {e}")

    module.exit_json(changed=True, msg="Cluster rescan completed",
                     cluster=result)


def mode_switch_to_multi_primary(module, mysqlsh_path, uri, password, params):
    """Handle mode=switch_to_multi_primary."""
    status_data = get_cluster_status(module, mysqlsh_path, uri, password)
    current_mode = get_topology_mode(status_data)

    if current_mode and 'multi' in current_mode.lower():
        module.exit_json(changed=False,
                         msg="Cluster is already in Multi-Primary mode")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg="Would switch to Multi-Primary mode")

    try:
        run_mysqlsh_script(module, mysqlsh_path, uri, password,
                           "dba.get_cluster().switch_to_multi_primary_mode()")
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to switch to multi-primary: {e}")

    module.exit_json(changed=True,
                     msg="Switched to Multi-Primary mode")


def mode_switch_to_single_primary(module, mysqlsh_path, uri, password, params):
    """Handle mode=switch_to_single_primary."""
    status_data = get_cluster_status(module, mysqlsh_path, uri, password)
    current_mode = get_topology_mode(status_data)

    if current_mode and 'single' in current_mode.lower():
        module.exit_json(changed=False,
                         msg="Cluster is already in Single-Primary mode")

    if module.check_mode:
        module.exit_json(changed=True,
                         msg="Would switch to Single-Primary mode")

    try:
        run_mysqlsh_script(module, mysqlsh_path, uri, password,
                           "dba.get_cluster().switch_to_single_primary_mode()")
    except MysqlShellError as e:
        module.fail_json(msg=f"Failed to switch to single-primary: {e}")

    module.exit_json(changed=True,
                     msg="Switched to Single-Primary mode")


MODE_HANDLERS = {
    'create': mode_create,
    'dissolve': mode_dissolve,
    'add_instance': mode_add_instance,
    'remove_instance': mode_remove_instance,
    'rejoin_instance': mode_rejoin_instance,
    'set_primary': mode_set_primary,
    'set_option': mode_set_option,
    'rescan': mode_rescan,
    'switch_to_multi_primary': mode_switch_to_multi_primary,
    'switch_to_single_primary': mode_switch_to_single_primary,
}


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
        mode=dict(type='str', required=True, choices=list(MODE_HANDLERS.keys())),
        name=dict(type='str'),
        instance=dict(type='str'),
        topology_mode=dict(type='str', default='single-primary',
                           choices=['single-primary', 'multi-primary']),
        recovery_method=dict(type='str', default='auto',
                             choices=['auto', 'clone', 'incremental']),
        option_name=dict(type='str'),
        option_value=dict(type='str'),
        force=dict(type='bool', default=False),
        wait_recovery=dict(type='int', default=0),
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
    mode = module.params['mode']

    mysqlsh_path = find_mysqlsh(module, mysqlsh_path_param)
    uri = build_uri(login_user, login_host, login_port, login_unix_socket)

    handler = MODE_HANDLERS[mode]
    handler(module, mysqlsh_path, uri, login_password, module.params)


if __name__ == '__main__':
    main()
