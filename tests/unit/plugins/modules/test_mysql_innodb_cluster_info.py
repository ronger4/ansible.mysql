# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ron Gershburg (@ronger4)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.ansible.mysql.plugins.modules.mysql_innodb_cluster_info import (
    extract_members,
    extract_primary,
    extract_routers,
)


SAMPLE_STATUS = {
    'clusterName': 'prodCluster',
    'defaultReplicaSet': {
        'status': 'OK',
        'topologyMode': 'Single-Primary',
        'groupName': 'group-uuid-123',
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
                'status': 'ONLINE',
                'mode': 'R/O',
                'version': '8.0.38',
            },
        },
    },
    'routers': {
        'app-server-1::system': {
            'hostname': 'app-server-1',
            'lastCheckIn': '2026-01-15 10:30:00',
            'version': '8.0.38',
        },
        'app-server-2::system': {
            'hostname': 'app-server-2',
            'lastCheckIn': '2026-01-15 10:29:55',
            'version': '8.0.38',
        },
    },
}


class TestExtractMembers:
    def test_extracts_all_members(self):
        members = extract_members(SAMPLE_STATUS)
        assert len(members) == 3

    def test_member_fields(self):
        members = extract_members(SAMPLE_STATUS)
        primary = next(m for m in members if m['address'] == 'primary-db:3306')
        assert primary['role'] == 'PRIMARY'
        assert primary['state'] == 'ONLINE'
        assert primary['version'] == '8.0.38'
        assert primary['mode'] == 'R/W'

    def test_empty_topology(self):
        status = {'defaultReplicaSet': {'topology': {}}}
        members = extract_members(status)
        assert members == []

    def test_missing_default_replica_set(self):
        members = extract_members({})
        assert members == []


class TestExtractPrimary:
    def test_finds_primary(self):
        primary = extract_primary(SAMPLE_STATUS)
        assert primary == 'primary-db:3306'

    def test_no_primary(self):
        status = {
            'defaultReplicaSet': {
                'topology': {
                    'node1:3306': {'memberRole': 'SECONDARY', 'status': 'ONLINE'},
                }
            }
        }
        primary = extract_primary(status)
        assert primary is None

    def test_empty_status(self):
        assert extract_primary({}) is None


class TestExtractRouters:
    def test_extracts_routers(self):
        routers = extract_routers(SAMPLE_STATUS)
        assert len(routers) == 2

    def test_router_fields(self):
        routers = extract_routers(SAMPLE_STATUS)
        r1 = next(r for r in routers if r['hostname'] == 'app-server-1')
        assert r1['name'] == 'app-server-1::system'
        assert r1['last_check_in'] == '2026-01-15 10:30:00'
        assert r1['version'] == '8.0.38'

    def test_no_routers(self):
        status = {'routers': {}}
        routers = extract_routers(status)
        assert routers == []

    def test_missing_routers_key(self):
        routers = extract_routers({})
        assert routers == []
