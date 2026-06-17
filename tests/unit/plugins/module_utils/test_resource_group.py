from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import pytest

from ansible_collections.ansible.mysql.plugins.module_utils.resource_group import (
    get_server_version_tuple,
    normalize_resource_group_enabled,
    normalize_resource_group_row,
    normalize_vcpu_ids,
    validate_resource_group_type,
    validate_thread_priority,
)
from ..utils import dummy_cursor_class


@pytest.mark.parametrize(
    'server_version,expected',
    [
        ('8.0.38', (8, 0, 38)),
        ('8.4.9-commercial', (8, 4, 9)),
        ('9.7.0-foo', (9, 7, 0)),
    ]
)
def test_get_server_version_tuple(server_version, expected):
    cursor = dummy_cursor_class(server_version, 'dict')
    assert get_server_version_tuple(cursor) == expected


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


@pytest.mark.parametrize(
    'input_,expected',
    [
        (True, True),
        (False, False),
        ('YES', True),
        ('0', False),
        (1, True),
    ]
)
def test_normalize_resource_group_enabled(input_, expected):
    assert normalize_resource_group_enabled(input_) == expected


def test_normalize_resource_group_row():
    row = {
        'RESOURCE_GROUP_NAME': 'reporting',
        'RESOURCE_GROUP_TYPE': 'USER',
        'RESOURCE_GROUP_ENABLED': 1,
        'VCPU_IDS': b'3,2,1,0',
        'THREAD_PRIORITY': 5,
    }

    assert normalize_resource_group_row(row) == {
        'name': 'reporting',
        'resource_group_type': 'USER',
        'enabled': True,
        'vcpu_ids': '0-3',
        'thread_priority': 5,
    }


@pytest.mark.parametrize(
    'resource_group_type,thread_priority',
    [
        ('USER', -1),
        ('SYSTEM', 1),
    ]
)
def test_validate_thread_priority_rejects_type_specific_invalid_values(resource_group_type, thread_priority):
    with pytest.raises(ValueError):
        validate_thread_priority(validate_resource_group_type(resource_group_type), thread_priority)
