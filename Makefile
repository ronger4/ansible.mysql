SHELL := /bin/bash

# To tell ansible-test and Make to not kill the containers on failure or
# end of tests. Disabled by default.
ifdef keep_containers_alive
	_keep_containers_alive = --docker-terminate never
endif

# This match what GitHub Action will do. Disabled by default.
ifdef continue_on_errors
	_continue_on_errors = --continue-on-error
endif

# Use ubuntu2604 for devel (ubuntu2204 is no longer supported),
# keep ubuntu2204 for stable branches.
ifeq ($(ansible),devel)
	_docker_image = ubuntu2604
else
	_docker_image = ubuntu2204
endif

# Set command variables based on database engine
# Required for MariaDB 11+ which no longer includes mysql named compatible
# executable symlinks
ifeq ($(db_engine_name),mysql)
	_command = mysqld
	_health_cmd = mysqladmin
else
	_command = mariadbd
	_health_cmd = mariadb-admin
endif

# Shared macros to reduce duplication between targets
define write_metadata
	@echo -n $(1) > tests/integration/db_engine_name
	@echo -n $(db_engine_version) > tests/integration/db_engine_version
	@echo -n $(connector_name) > tests/integration/connector_name
	@echo -n $(connector_version) > tests/integration/connector_version
	@echo -n $(ansible) > tests/integration/ansible
endef

define run_ansible_test
	mkdir -p .venv/$(ansible)
	python$(local_python_version) -m venv .venv/$(ansible)
	source .venv/$(ansible)/bin/activate; \
	python$(local_python_version) -m ensurepip; \
	python$(local_python_version) -m pip install --disable-pip-version-check \
	https://github.com/ansible/ansible/archive/$(ansible).tar.gz; \
	set -x; \
	ansible-test integration $(1) -v --color --coverage --diff \
	--docker $(_docker_image) \
	--docker-network podman $(_continue_on_errors) $(_keep_containers_alive); \
	set +x
endef

define wait_healthy_and_restart
	while ! podman healthcheck run primary && [[ "$$SECONDS" -lt 120 ]]; do sleep 1; done
	podman restart -t 30 primary
	while ! podman healthcheck run replica1 && [[ "$$SECONDS" -lt 120 ]]; do sleep 1; done
	podman restart -t 30 replica1
	while ! podman healthcheck run replica2 && [[ "$$SECONDS" -lt 120 ]]; do sleep 1; done
	podman restart -t 30 replica2
	while ! podman healthcheck run primary && [[ "$$SECONDS" -lt 120 ]]; do sleep 1; done
endef

define cleanup_metadata
	rm -f tests/integration/db_engine_name
	rm -f tests/integration/db_engine_version
	rm -f tests/integration/connector_name
	rm -f tests/integration/connector_version
	rm -f tests/integration/ansible
endef

define cleanup_containers
	@if [ -z "$(keep_containers_alive)" ]; then \
		podman stop --time 0 --ignore primary replica1 replica2; \
		podman rm --ignore --volumes primary replica1 replica2; \
	fi
endef

.PHONY: test-integration
test-integration:
	$(call write_metadata,$(db_engine_name))

	# Create podman network for systems missing it. Error can be ignored
	podman network create podman || true
	podman run \
		--detach \
		--replace \
		--name primary \
		--env MARIADB_ROOT_PASSWORD=msandbox \
		--env MYSQL_ROOT_PASSWORD=msandbox \
		--network podman \
		--publish 3307:3306 \
		--health-cmd '$(_health_cmd) ping -P 3306 -pmsandbox | grep alive || exit 1' \
		docker.io/library/$(db_engine_name):$(db_engine_version) \
		$(_command)
	podman run \
		--detach \
		--replace \
		--name replica1 \
		--env MARIADB_ROOT_PASSWORD=msandbox \
		--env MYSQL_ROOT_PASSWORD=msandbox \
		--network podman \
		--publish 3308:3306 \
		--health-cmd '$(_health_cmd) ping -P 3306 -pmsandbox | grep alive || exit 1' \
		docker.io/library/$(db_engine_name):$(db_engine_version) \
		$(_command)
	podman run \
		--detach \
		--replace \
		--name replica2 \
		--env MARIADB_ROOT_PASSWORD=msandbox \
		--env MYSQL_ROOT_PASSWORD=msandbox \
		--network podman \
		--publish 3309:3306 \
		--health-cmd '$(_health_cmd) ping -P 3306 -pmsandbox | grep alive || exit 1' \
		docker.io/library/$(db_engine_name):$(db_engine_version) \
		$(_command)
	# Setup replication and restart containers using the same subshell to keep variables alive
	db_ver=$(db_engine_version); \
	maj="$${db_ver%.*.*}"; \
	maj_min="$${db_ver%.*}"; \
	min="$${maj_min#*.}"; \
	if [[ "$(db_engine_name)" == "mysql" && "$$maj" -eq 8 && "$$min" -ge 2 ]]; then \
		prima_conf='[mysqld]\\nserver-id=1\\nlog-bin=/var/lib/mysql/primary-bin\\nmysql-native-password=1'; \
		repl1_conf='[mysqld]\\nserver-id=2\\nlog-bin=/var/lib/mysql/replica1-bin\\nmysql-native-password=1'; \
		repl2_conf='[mysqld]\\nserver-id=3\\nlog-bin=/var/lib/mysql/replica2-bin\\nmysql-native-password=1'; \
	else \
		prima_conf='[mysqld]\\nserver-id=1\\nlog-bin=/var/lib/mysql/primary-bin'; \
		repl1_conf='[mysqld]\\nserver-id=2\\nlog-bin=/var/lib/mysql/replica1-bin'; \
		repl2_conf='[mysqld]\\nserver-id=3\\nlog-bin=/var/lib/mysql/replica2-bin'; \
	fi; \
	podman exec -e cnf="$$prima_conf" primary bash -c 'echo -e "$${cnf//\\n/\n}" > /etc/mysql/conf.d/replication.cnf'; \
	podman exec -e cnf="$$repl1_conf" replica1 bash -c 'echo -e "$${cnf//\\n/\n}" > /etc/mysql/conf.d/replication.cnf'; \
	podman exec -e cnf="$$repl2_conf" replica2 bash -c 'echo -e "$${cnf//\\n/\n}" > /etc/mysql/conf.d/replication.cnf'
	$(call wait_healthy_and_restart)
	# Run tests
	$(call run_ansible_test,$(target))

	$(call cleanup_metadata)
	$(call cleanup_containers)

# InnoDB Cluster integration tests require a separate target because they need
# GTID and Group Replication settings that conflict with dump/import tests.
.PHONY: test-integration-innodb-cluster
test-integration-innodb-cluster:
	$(call write_metadata,mysql)

	podman network create podman || true
	podman run \
		--detach \
		--replace \
		--name primary \
		--hostname primary \
		--env MYSQL_ROOT_PASSWORD=msandbox \
		--network podman \
		--publish 3307:3306 \
		--health-cmd 'mysqladmin ping -P 3306 -pmsandbox | grep alive || exit 1' \
		docker.io/library/mysql:$(db_engine_version) \
		mysqld
	podman run \
		--detach \
		--replace \
		--name replica1 \
		--hostname replica1 \
		--env MYSQL_ROOT_PASSWORD=msandbox \
		--network podman \
		--publish 3308:3306 \
		--health-cmd 'mysqladmin ping -P 3306 -pmsandbox | grep alive || exit 1' \
		docker.io/library/mysql:$(db_engine_version) \
		mysqld
	podman run \
		--detach \
		--replace \
		--name replica2 \
		--hostname replica2 \
		--env MYSQL_ROOT_PASSWORD=msandbox \
		--network podman \
		--publish 3309:3306 \
		--health-cmd 'mysqladmin ping -P 3306 -pmsandbox | grep alive || exit 1' \
		docker.io/library/mysql:$(db_engine_version) \
		mysqld
	# Configure MySQL for InnoDB Cluster (GTID + GR prerequisites)
	db_ver=$(db_engine_version); \
	maj="$${db_ver%.*.*}"; \
	maj_min="$${db_ver%.*}"; \
	min="$${maj_min#*.}"; \
	if [[ "$$maj" -eq 8 && "$$min" -ge 2 ]]; then \
		prima_conf='[mysqld]\\nserver-id=1\\nlog-bin=/var/lib/mysql/primary-bin\\nmysql-native-password=1\\ngtid_mode=ON\\nenforce_gtid_consistency=ON\\nbinlog_transaction_dependency_tracking=WRITESET\\nreplica_parallel_workers=4\\nreplica_preserve_commit_order=ON'; \
		repl1_conf='[mysqld]\\nserver-id=2\\nlog-bin=/var/lib/mysql/replica1-bin\\nmysql-native-password=1\\ngtid_mode=ON\\nenforce_gtid_consistency=ON\\nbinlog_transaction_dependency_tracking=WRITESET\\nreplica_parallel_workers=4\\nreplica_preserve_commit_order=ON'; \
		repl2_conf='[mysqld]\\nserver-id=3\\nlog-bin=/var/lib/mysql/replica2-bin\\nmysql-native-password=1\\ngtid_mode=ON\\nenforce_gtid_consistency=ON\\nbinlog_transaction_dependency_tracking=WRITESET\\nreplica_parallel_workers=4\\nreplica_preserve_commit_order=ON'; \
	else \
		prima_conf='[mysqld]\\nserver-id=1\\nlog-bin=/var/lib/mysql/primary-bin\\ngtid_mode=ON\\nenforce_gtid_consistency=ON\\nbinlog_transaction_dependency_tracking=WRITESET\\nreplica_parallel_workers=4\\nreplica_preserve_commit_order=ON'; \
		repl1_conf='[mysqld]\\nserver-id=2\\nlog-bin=/var/lib/mysql/replica1-bin\\ngtid_mode=ON\\nenforce_gtid_consistency=ON\\nbinlog_transaction_dependency_tracking=WRITESET\\nreplica_parallel_workers=4\\nreplica_preserve_commit_order=ON'; \
		repl2_conf='[mysqld]\\nserver-id=3\\nlog-bin=/var/lib/mysql/replica2-bin\\ngtid_mode=ON\\nenforce_gtid_consistency=ON\\nbinlog_transaction_dependency_tracking=WRITESET\\nreplica_parallel_workers=4\\nreplica_preserve_commit_order=ON'; \
	fi; \
	podman exec -e cnf="$$prima_conf" primary bash -c 'echo -e "$${cnf//\\n/\n}" > /etc/mysql/conf.d/replication.cnf'; \
	podman exec -e cnf="$$repl1_conf" replica1 bash -c 'echo -e "$${cnf//\\n/\n}" > /etc/mysql/conf.d/replication.cnf'; \
	podman exec -e cnf="$$repl2_conf" replica2 bash -c 'echo -e "$${cnf//\\n/\n}" > /etc/mysql/conf.d/replication.cnf'
	$(call wait_healthy_and_restart)
	# Write container IPs after restart (podman may reassign IPs)
	@echo -n $$(podman inspect primary --format '{{.NetworkSettings.Networks.podman.IPAddress}}') > tests/integration/primary_ip
	@echo -n $$(podman inspect replica1 --format '{{.NetworkSettings.Networks.podman.IPAddress}}') > tests/integration/replica1_ip
	@echo -n $$(podman inspect replica2 --format '{{.NetworkSettings.Networks.podman.IPAddress}}') > tests/integration/replica2_ip
	# Add /etc/hosts entries so containers can resolve each other by hostname
	@primary_ip=$$(cat tests/integration/primary_ip); \
	replica1_ip=$$(cat tests/integration/replica1_ip); \
	replica2_ip=$$(cat tests/integration/replica2_ip); \
	hosts_entries="$$primary_ip primary\n$$replica1_ip replica1\n$$replica2_ip replica2"; \
	podman exec primary bash -c "echo -e '$$hosts_entries' >> /etc/hosts"; \
	podman exec replica1 bash -c "echo -e '$$hosts_entries' >> /etc/hosts"; \
	podman exec replica2 bash -c "echo -e '$$hosts_entries' >> /etc/hosts"
	# Run tests
	$(call run_ansible_test,test_mysql_innodb_cluster)

	$(call cleanup_metadata)
	rm -f tests/integration/primary_ip
	rm -f tests/integration/replica1_ip
	rm -f tests/integration/replica2_ip
	$(call cleanup_containers)
