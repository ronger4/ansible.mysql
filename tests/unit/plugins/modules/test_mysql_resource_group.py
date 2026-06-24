# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from ansible_collections.ansible.mysql.plugins.modules.mysql_resource_group import (
    build_alter_query,
    build_create_query,
    build_drop_query,
    execute_query,
    normalize_resource_group_inputs,
)


@pytest.mark.parametrize(
    'resource_group_type,vcpu_ids,expected',
    [
        ('user', '3,2,1,0', ('USER', '0-3')),
        (None, None, (None, None)),
    ]
)
def test_normalize_resource_group_inputs(resource_group_type, vcpu_ids, expected):
    assert normalize_resource_group_inputs(resource_group_type, vcpu_ids) == expected


def test_build_create_query():
    assert build_create_query(
        'reporting',
        'USER',
        vcpu_ids='0-3',
        thread_priority=5,
        enabled=False,
    ) == "CREATE RESOURCE GROUP `reporting` TYPE = USER VCPU = 0-3 THREAD_PRIORITY = 5 DISABLE"


@pytest.mark.parametrize(
    'force,expected',
    [
        (False, "DROP RESOURCE GROUP `reporting`"),
        (True, "DROP RESOURCE GROUP `reporting` FORCE"),
    ]
)
def test_build_drop_query(force, expected):
    assert build_drop_query('reporting', force=force) == expected


def test_execute_query_does_not_fetch_after_execute():
    cursor = MagicMock()

    execute_query(cursor, 'DROP RESOURCE GROUP `reporting`')

    cursor.execute.assert_called_once_with('DROP RESOURCE GROUP `reporting`')
    cursor.fetchall.assert_not_called()


def test_build_alter_query_returns_none_when_nothing_changes():
    current = {
        'name': 'reporting',
        'resource_group_type': 'USER',
        'vcpu_ids': '0-3',
        'thread_priority': 5,
        'enabled': True,
    }

    assert build_alter_query(
        'reporting',
        current,
        resource_group_type='USER',
        vcpu_ids='0-3',
        thread_priority=5,
        enabled=True,
    ) is None


def test_build_alter_query_updates_only_changed_fields():
    current = {
        'name': 'reporting',
        'resource_group_type': 'USER',
        'vcpu_ids': '0-3',
        'thread_priority': 0,
        'enabled': True,
    }

    assert build_alter_query(
        'reporting',
        current,
        resource_group_type='USER',
        vcpu_ids='4-7',
        thread_priority=10,
        enabled=False,
    ) == "ALTER RESOURCE GROUP `reporting` VCPU = 4-7 THREAD_PRIORITY = 10 DISABLE"


def test_build_alter_query_fails_on_resource_group_type_change():
    current = {
        'name': 'reporting',
        'resource_group_type': 'USER',
        'vcpu_ids': '0-3',
        'thread_priority': 0,
        'enabled': True,
    }

    with pytest.raises(ValueError, match='resource_group_type is immutable'):
        build_alter_query(
            'reporting',
            current,
            resource_group_type='SYSTEM',
        )


def test_build_create_query_allows_system_negative_priority():
    assert build_create_query(
        'system_group',
        'SYSTEM',
        thread_priority=-5,
    ) == "CREATE RESOURCE GROUP `system_group` TYPE = SYSTEM THREAD_PRIORITY = -5"
