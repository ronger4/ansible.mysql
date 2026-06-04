# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ron Gershburg (@ronger4)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import patch, MagicMock

from ansible_collections.ansible.mysql.plugins.modules.mysql_innodb_cluster import (
    cluster_exists,
    instance_in_cluster,
    get_current_primary,
    get_topology_mode,
)
from ansible_collections.ansible.mysql.plugins.module_utils.mysqlsh import (
    MysqlShellError,
)


SAMPLE_STATUS = {
    'clusterName': 'testCluster',
    'defaultReplicaSet': {
        'status': 'OK',
        'topologyMode': 'Single-Primary',
        'groupName': 'abc-123',
        'topology': {
            'primary-db:3306': {
                'memberRole': 'PRIMARY',
                'status': 'ONLINE',
                'mode': 'R/W',
                'version': '8.0.38',
            },
            'replica1-db:3306': {
                'memberRole': 'SECONDARY',
                'status': 'ONLINE',
                'mode': 'R/O',
                'version': '8.0.38',
            },
            'replica2-db:3306': {
                'memberRole': 'SECONDARY',
                'status': 'RECOVERING',
                'mode': 'R/O',
                'version': '8.0.38',
            },
        },
    },
}


class TestClusterExists:
    @patch('ansible_collections.ansible.mysql.plugins.modules.mysql_innodb_cluster.run_mysqlsh')
    def test_cluster_exists_true(self, mock_run):
        mock_run.return_value = {'clusterName': 'test'}
        module = MagicMock()
        assert cluster_exists(module, '/usr/bin/mysqlsh', 'root@localhost:3306', 'pass') is True

    @patch('ansible_collections.ansible.mysql.plugins.modules.mysql_innodb_cluster.run_mysqlsh')
    def test_cluster_exists_false(self, mock_run):
        mock_run.side_effect = MysqlShellError('no cluster')
        module = MagicMock()
        assert cluster_exists(module, '/usr/bin/mysqlsh', 'root@localhost:3306', 'pass') is False


class TestInstanceInCluster:
    def test_instance_online(self):
        state = instance_in_cluster(SAMPLE_STATUS, 'primary-db:3306')
        assert state == 'ONLINE'

    def test_instance_recovering(self):
        state = instance_in_cluster(SAMPLE_STATUS, 'replica2-db:3306')
        assert state == 'RECOVERING'

    def test_instance_not_found(self):
        state = instance_in_cluster(SAMPLE_STATUS, 'unknown-db:3306')
        assert state is None

    def test_instance_with_user_prefix(self):
        state = instance_in_cluster(SAMPLE_STATUS, 'admin@replica1-db:3306')
        assert state == 'ONLINE'

    def test_none_status_data(self):
        state = instance_in_cluster(None, 'primary-db:3306')
        assert state is None


class TestGetCurrentPrimary:
    def test_finds_primary(self):
        primary = get_current_primary(SAMPLE_STATUS)
        assert primary == 'primary-db:3306'

    def test_no_status_data(self):
        assert get_current_primary(None) is None

    def test_no_primary_in_topology(self):
        status = {
            'defaultReplicaSet': {
                'topology': {
                    'node1:3306': {'memberRole': 'SECONDARY', 'status': 'ONLINE'},
                }
            }
        }
        assert get_current_primary(status) is None


class TestGetTopologyMode:
    def test_single_primary(self):
        mode = get_topology_mode(SAMPLE_STATUS)
        assert mode == 'Single-Primary'

    def test_multi_primary(self):
        status = {
            'defaultReplicaSet': {
                'topologyMode': 'Multi-Primary',
                'topology': {},
            }
        }
        mode = get_topology_mode(status)
        assert mode == 'Multi-Primary'

    def test_none_status(self):
        assert get_topology_mode(None) is None
