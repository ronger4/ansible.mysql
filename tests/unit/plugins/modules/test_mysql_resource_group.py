# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import pytest

from ansible_collections.ansible.mysql.plugins.modules.mysql_resource_group import (
    build_alter_query,
    build_create_query,
    normalize_vcpu_ids,
)


@pytest.mark.parametrize(
    'input_,output',
    [
        ('0-3,9,10', '0-3,9-10'),
        ('9,10,0,1,2,3', '0-3,9-10'),
        ('3,2,1,0', '0-3'),
        ('0', '0'),
        (b'0-15', '0-15'),
        (None, None),
    ]
)
def test_normalize_vcpu_ids(input_, output):
    assert normalize_vcpu_ids(input_) == output


def test_build_create_query():
    assert build_create_query(
        'reporting',
        'USER',
        vcpu_ids='3,2,1,0',
        thread_priority=5,
        enabled=False,
    ) == "CREATE RESOURCE GROUP `reporting` TYPE = USER VCPU = 0-3 THREAD_PRIORITY = 5 DISABLE"


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
        vcpu_ids='3,2,1,0',
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
        vcpu_ids='4,5,6,7',
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
