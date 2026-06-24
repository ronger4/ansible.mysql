# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from ansible_collections.ansible.mysql.plugins.modules.mysql_resource_group_info import get_resource_groups_info


def test_get_info_returns_normalized_resource_groups():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {
            'RESOURCE_GROUP_NAME': 'USR_default',
            'RESOURCE_GROUP_TYPE': 'USER',
            'RESOURCE_GROUP_ENABLED': 'YES',
            'VCPU_IDS': '0-3',
            'THREAD_PRIORITY': 0,
        },
        {
            'RESOURCE_GROUP_NAME': 'reporting',
            'RESOURCE_GROUP_TYPE': 'USER',
            'RESOURCE_GROUP_ENABLED': 'NO',
            'VCPU_IDS': '3,2,1,0',
            'THREAD_PRIORITY': 5,
        },
    ]

    assert get_resource_groups_info(cursor) == {
        'resource_groups': [
            {
                'name': 'USR_default',
                'resource_group_type': 'USER',
                'enabled': True,
                'vcpu_ids': '0-3',
                'thread_priority': 0,
            },
            {
                'name': 'reporting',
                'resource_group_type': 'USER',
                'enabled': False,
                'vcpu_ids': '0-3',
                'thread_priority': 5,
            },
        ]
    }
    cursor.execute.assert_called_once_with(
        'SELECT RESOURCE_GROUP_NAME, RESOURCE_GROUP_TYPE, RESOURCE_GROUP_ENABLED, VCPU_IDS, THREAD_PRIORITY '
        'FROM INFORMATION_SCHEMA.RESOURCE_GROUPS ORDER BY RESOURCE_GROUP_NAME'
    )


def test_get_info_filters_by_name():
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {
            'RESOURCE_GROUP_NAME': 'reporting',
            'RESOURCE_GROUP_TYPE': 'USER',
            'RESOURCE_GROUP_ENABLED': 'NO',
            'VCPU_IDS': '7,6,5,4',
            'THREAD_PRIORITY': 10,
        }
    ]

    assert get_resource_groups_info(cursor, name='reporting') == {
        'resource_groups': [
            {
                'name': 'reporting',
                'resource_group_type': 'USER',
                'enabled': False,
                'vcpu_ids': '4-7',
                'thread_priority': 10,
            }
        ]
    }
    cursor.execute.assert_called_once_with(
        'SELECT RESOURCE_GROUP_NAME, RESOURCE_GROUP_TYPE, RESOURCE_GROUP_ENABLED, VCPU_IDS, THREAD_PRIORITY '
        'FROM INFORMATION_SCHEMA.RESOURCE_GROUPS WHERE RESOURCE_GROUP_NAME = %s ORDER BY RESOURCE_GROUP_NAME',
        ('reporting',)
    )
