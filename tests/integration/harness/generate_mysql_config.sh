#!/usr/bin/env bash
# Generate a mysqld config snippet for a given server profile and version.
# Used by both the Makefile (podman) and CI workflow (docker) to avoid
# duplicating version-specific config logic.
#
# Usage:
#   generate_mysql_config.sh --server-id 1 --profile replication --db-version 8.0.38
#   generate_mysql_config.sh --server-id 2 --profile innodb_cluster --db-version 8.4.9
#
# Profiles:
#   replication     - basic replication (server-id, log-bin, optional mysql-native-password)
#   innodb_cluster  - replication + GTID, GR prerequisites, parallel applier settings

set -euo pipefail

server_id=""
profile=""
db_version=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --server-id)  server_id="$2"; shift 2 ;;
        --profile)    profile="$2"; shift 2 ;;
        --db-version) db_version="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$server_id" || -z "$profile" || -z "$db_version" ]]; then
    echo "Usage: $0 --server-id N --profile {replication|innodb_cluster} --db-version X.Y.Z" >&2
    exit 1
fi

log_bin_name="node${server_id}-bin"

# Version parsing: MySQL >= 8.2 needs mysql-native-password=1 for pymysql auth
maj="${db_version%%.*}"
maj_min="${db_version%.*}"
min="${maj_min#*.}"
needs_native_password=false
if [[ "$maj" -eq 8 && "$min" -ge 2 ]] || [[ "$maj" -ge 9 ]]; then
    needs_native_password=true
fi

# Build config
config="[mysqld]"
config+="\nserver-id=${server_id}"
config+="\nlog-bin=/var/lib/mysql/${log_bin_name}"

if [[ "$needs_native_password" == "true" ]]; then
    config+="\nmysql-native-password=1"
fi

if [[ "$profile" == "innodb_cluster" ]]; then
    config+="\ngtid_mode=ON"
    config+="\nenforce_gtid_consistency=ON"
    config+="\nbinlog_format=ROW"
    config+="\nlog_replica_updates=ON"
    config+="\nreplica_parallel_workers=4"
    config+="\nreplica_preserve_commit_order=ON"
fi

echo -e "$config"
