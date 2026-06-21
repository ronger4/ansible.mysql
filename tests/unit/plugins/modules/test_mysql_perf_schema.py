from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from ansible_collections.ansible.mysql.plugins.modules.mysql_perf_schema import MySQL_Perf_Schema


def test_apply_in_check_mode_returns_predicted_queries_without_executing_updates():
    support_rows = [
        {'TABLE_NAME': 'setup_instruments', 'COLUMN_NAME': 'NAME'},
        {'TABLE_NAME': 'setup_instruments', 'COLUMN_NAME': 'ENABLED'},
        {'TABLE_NAME': 'setup_instruments', 'COLUMN_NAME': 'TIMED'},
    ]
    current_rows = [
        {'NAME': 'wait/io/table/sql/handler', 'ENABLED': 'NO', 'TIMED': 'NO'},
    ]

    cursor = MagicMock()

    def execute_side_effect(query, params=None):
        if query.startswith('SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS'):
            cursor.fetchall.return_value = support_rows
        elif query == 'SELECT * FROM performance_schema.setup_instruments':
            cursor.fetchall.return_value = current_rows
        else:
            raise AssertionError('Unexpected query: %s' % query)

    cursor.execute.side_effect = execute_side_effect

    module = MagicMock()
    module.check_mode = True
    executor = MySQL_Perf_Schema(module, cursor)

    result = executor.apply({
        'instruments': [
            {'name': 'wait/io/table/sql/handler', 'enabled': True, 'timed': True},
        ]
    })

    assert result == {
        'changed': True,
        'queries': [
            "UPDATE performance_schema.setup_instruments "
            "SET ENABLED = 'YES', TIMED = 'YES' "
            "WHERE NAME = 'wait/io/table/sql/handler'"
        ],
        'instruments': [
            {
                'name': 'wait/io/table/sql/handler',
                'enabled': True,
                'timed': True,
            }
        ],
    }
    assert cursor.execute.call_count == 2


def test_apply_executes_mutations_and_returns_rows_for_multiple_sections():
    support_rows = [
        {'TABLE_NAME': 'setup_consumers', 'COLUMN_NAME': 'NAME'},
        {'TABLE_NAME': 'setup_consumers', 'COLUMN_NAME': 'ENABLED'},
        {'TABLE_NAME': 'setup_actors', 'COLUMN_NAME': 'HOST'},
        {'TABLE_NAME': 'setup_actors', 'COLUMN_NAME': 'USER'},
        {'TABLE_NAME': 'setup_actors', 'COLUMN_NAME': 'ROLE'},
        {'TABLE_NAME': 'setup_actors', 'COLUMN_NAME': 'ENABLED'},
        {'TABLE_NAME': 'setup_actors', 'COLUMN_NAME': 'HISTORY'},
    ]
    consumer_rows = [
        {'NAME': 'events_waits_current', 'ENABLED': 'NO'},
    ]
    actor_rows = []

    cursor = MagicMock()

    def execute_side_effect(query, params=None):
        if query.startswith('SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS'):
            cursor.fetchall.return_value = support_rows
        elif query == 'SELECT * FROM performance_schema.setup_consumers':
            cursor.fetchall.return_value = consumer_rows
        elif query == 'SELECT * FROM performance_schema.setup_actors':
            cursor.fetchall.return_value = actor_rows
        else:
            cursor.fetchall.return_value = []

    cursor.execute.side_effect = execute_side_effect

    module = MagicMock()
    module.check_mode = False
    executor = MySQL_Perf_Schema(module, cursor)

    result = executor.apply({
        'consumers': [
            {'name': 'events_waits_current', 'enabled': True},
        ],
        'actors': [
            {'user': 'app', 'host': '%', 'role': '%', 'enabled': True, 'history': False},
        ],
    })

    assert result == {
        'changed': True,
        'queries': [
            "UPDATE performance_schema.setup_consumers "
            "SET ENABLED = 'YES' "
            "WHERE NAME = 'events_waits_current'",
            "INSERT INTO performance_schema.setup_actors (HOST, USER, ROLE, ENABLED, HISTORY) "
            "VALUES ('%', 'app', '%', 'YES', 'NO')",
        ],
        'consumers': [
            {'name': 'events_waits_current', 'enabled': True},
        ],
        'actors': [
            {'user': 'app', 'host': '%', 'role': '%', 'enabled': True, 'history': False},
        ],
    }
    assert cursor.execute.call_args_list[2][0][0].startswith('UPDATE performance_schema.setup_consumers')
    assert cursor.execute.call_args_list[4][0][0].startswith('INSERT INTO performance_schema.setup_actors')
