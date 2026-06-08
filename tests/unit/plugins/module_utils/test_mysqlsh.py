# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ron Gershburg (@ronger4)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import pytest

from ansible_collections.ansible.mysql.plugins.module_utils.mysqlsh import (
    build_uri,
    parse_json_output,
    MysqlShellError,
)


class TestBuildUri:
    def test_basic_uri(self):
        uri = build_uri('root', 'dbhost', 3306)
        assert uri == 'root@dbhost:3306'

    def test_custom_port(self):
        uri = build_uri('admin', '192.168.1.10', 3307)
        assert uri == 'admin@192.168.1.10:3307'

    def test_socket_overrides_host(self):
        uri = build_uri('root', 'dbhost', 3306,
                         socket='/var/run/mysqld/mysqld.sock')
        assert uri == 'root@localhost?socket=/var/run/mysqld/mysqld.sock'


class TestParseJsonOutput:
    def test_success_with_json(self):
        data = {'clusterName': 'myCluster', 'status': 'OK'}
        stdout = json.dumps(data)
        result = parse_json_output(stdout, '', 0)
        assert result == data

    def test_success_empty_output(self):
        result = parse_json_output('', '', 0)
        assert result is None

    def test_success_whitespace_only(self):
        result = parse_json_output('   \n  ', '', 0)
        assert result is None

    def test_failure_raises_error(self):
        error_data = {'error': {'message': 'Cluster does not exist'}}
        stdout = json.dumps(error_data)
        with pytest.raises(MysqlShellError) as exc_info:
            parse_json_output(stdout, '', 1)
        assert 'Cluster does not exist' in str(exc_info.value)

    def test_failure_with_stderr(self):
        with pytest.raises(MysqlShellError) as exc_info:
            parse_json_output('', 'ERROR: connection refused', 1)
        assert 'connection refused' in str(exc_info.value)

    def test_failure_with_unparseable_stdout(self):
        with pytest.raises(MysqlShellError) as exc_info:
            parse_json_output('not json at all', '', 1)
        assert 'not json at all' in str(exc_info.value)

    def test_failure_no_output(self):
        with pytest.raises(MysqlShellError) as exc_info:
            parse_json_output('', '', 1)
        assert 'exit code 1' in str(exc_info.value)

    def test_success_invalid_json_raises_error(self):
        with pytest.raises(MysqlShellError) as exc_info:
            parse_json_output('this is {not valid json', '', 0)
        assert 'Failed to parse' in str(exc_info.value)

    def test_error_with_message_field(self):
        error_data = {'message': 'Something went wrong'}
        stdout = json.dumps(error_data)
        with pytest.raises(MysqlShellError) as exc_info:
            parse_json_output(stdout, '', 1)
        assert 'Something went wrong' in str(exc_info.value)


class TestMysqlShellError:
    def test_attributes(self):
        e = MysqlShellError('test error', rc=1, stdout='out', stderr='err')
        assert str(e) == 'test error'
        assert e.rc == 1
        assert e.stdout == 'out'
        assert e.stderr == 'err'

    def test_defaults(self):
        e = MysqlShellError('msg')
        assert e.rc is None
        assert e.stdout is None
        assert e.stderr is None
