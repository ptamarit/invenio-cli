# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
# Copyright (C) 2025 Graz University of Technology.
#
# Invenio-Cli is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module to ease the creation and management of applications."""

from ..helpers.docker_helper import DockerHelper
from ..helpers.versions import rdm_version
from .packages import PackagesCommands
from .services import ServicesCommands
from .steps import FunctionStep
from .translations import TranslationsCommands


class ContainersCommands(ServicesCommands):
    """Containerized environment CLI commands."""

    def __init__(self, cli_config, docker_helper=None):
        """Constructor."""
        docker_helper = docker_helper or DockerHelper(
            cli_config.get_project_shortname(), local=False
        )

        super().__init__(cli_config, docker_helper)

    def build(self, pull=True, cache=True):
        """Return the steps to build images.

        :param pull: Attempt to pull newer versions of the images.
        :param cache: Use cached images and layers.
        """
        steps = [
            FunctionStep(
                func=lambda: PackagesCommands(self.cli_config).is_locked(),
                message="Checking if dependencies are locked.",
            ),
            FunctionStep(
                func=self.docker_helper.build_images,
                args={"pull": pull, "cache": cache},
                message="Building images...",
            ),
        ]

        return steps

    def _cleanup(self, project_shortname="/opt/var/instance/"):
        """Steps to cleanup commands."""
        steps = [
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio shell --no-term-title -c \"import redis; redis.StrictRedis.from_url(app.config['CACHE_REDIS_URL']).flushall(); print('Cache cleared')\"",  # noqa
                },
                message="Flushing redis cache...",
            ),
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio db destroy --yes-i-know",
                },
                message="Deleting database...",
            ),
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio index destroy --force --yes-i-know",
                },
                message="Deleting indices...",
            ),
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio index queue init purge",
                },
                message="Purging queues...",
            ),
            FunctionStep(
                func=self.cli_config.update_services_setup,
                args={"is_setup": False},
                message="Updating service setup status (False)...",
            ),
        ]

        return steps

    def _setup(self, project_shortname="/opt/var/instance/"):
        """Steps to initialize services."""
        steps = [
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio db init create",
                },
                message="Creating database...",
            ),
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio files location create --default default-location ${INVENIO_INSTANCE_PATH}/data",  # noqa
                },
                message="Creating files location...",
            ),
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio roles create admin",
                },
                message="Creating admin role...",
            ),
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio access allow superuser-access role admin",
                },
                message="Assigning superuser access to admin role...",
            ),
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio index init",
                },
                message="Creating indices...",
            ),
            FunctionStep(
                func=self.cli_config.update_services_setup,
                args={"is_setup": True},
                message="Updating service setup status (True)...",
            ),
        ]

        if rdm_version()[0] >= 10:
            steps.extend(
                [
                    FunctionStep(
                        func=self.docker_helper.execute_cli_command,
                        args={
                            "project_shortname": project_shortname,
                            "command": "invenio rdm-records custom-fields init",
                        },
                        message="Creating custom fields for records...",
                    ),
                    FunctionStep(
                        func=self.docker_helper.execute_cli_command,
                        args={
                            "project_shortname": project_shortname,
                            "command": "invenio communities custom-fields init",
                        },
                        message="Creating custom fields for communities...",
                    ),
                ]
            )

        if rdm_version()[0] >= 11:
            steps.extend(self.rdm_fixtures(project_shortname))
            steps.extend(self.translations(project_shortname))

        if rdm_version()[0] >= 12:
            steps.extend(self.declare_queues(project_shortname))

        return steps

    def demo(self, project_shortname):
        """Steps to demo records into the instance."""
        steps = [
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio rdm-records demo",
                },
                message="Creating demo records...",
            )
        ]

        return steps

    def declare_queues(self, project_shortname):
        """Steps to declare the MQ queues required for statistics, etc."""
        steps = [
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio queues declare",
                },
                message="Declaring queues...",
            )
        ]
        return steps

    def fixtures(self, project_shortname):
        """Steps to set up the required fixtures for the instance."""
        steps = [
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio rdm-records fixtures",
                },
                message="Creating records fixtures...",
            )
        ]

        return steps

    def rdm_fixtures(self, project_shortname):
        """Steps to set up the rdm fixtures for the instance."""
        steps = [
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": "invenio rdm fixtures",
                },
                message="Creating rdm fixtures...",
            )
        ]

        return steps

    def translations(self, project_shortname):
        """Steps to compile translations for the instance."""
        commands = TranslationsCommands(
            self.cli_config,
            project_path=self.cli_config.get_project_dir(),
            # we use INVENIO_INSTANCE_PATH that is set in the Dockerfile as
            # config.instance_path is set only in development `install` command
            instance_path="${INVENIO_INSTANCE_PATH}",
        )
        cmd = commands.compile(
            # instance path inside the container
            directory="${INVENIO_INSTANCE_PATH}/translations",
            symlink=False,
        )
        cmd = cmd[0].cmd  # extract compilation command
        cmd = " ".join(cmd)  # convert to string

        return [
            FunctionStep(
                func=self.docker_helper.execute_cli_command,
                args={
                    "project_shortname": project_shortname,
                    "command": cmd,
                },
                message="Compiling message catalog...",
                skippable=True,
            ),
        ]

    def setup(self, force, demo_data=True, stop=False, services=True):
        """Return the steps to setup containerize services.

        :param force: Remove existing content (db, indices, etc.).
        :param demo_data: Include demo records.
        :param stop: Stop services after setup.
        """
        steps = []

        if services:
            steps.append(
                FunctionStep(
                    func=self.ensure_containers_running,
                    message="Making sure containers are up...",
                )
            )

        project_shortname = self.cli_config.get_project_shortname()

        if force:
            steps.extend(self._cleanup(project_shortname))

        steps.extend(self._setup(project_shortname))
        steps.extend(self.fixtures(project_shortname))

        if demo_data:
            steps.extend(self.demo(project_shortname))

        if stop:
            steps.append(
                FunctionStep(
                    func=self.docker_helper.stop_containers,
                    message="Stopping containers....",
                )
            )

        return steps

    def start(
        self, lock=False, build=False, setup=False, demo_data=True, services=True
    ):
        """Return the steps to start service and application containers.

        :param lock: Lock dependencies.
        :param build: Build containers if not built.
        :param setup: Setup services (db, indices, etc.).
        :param demo_data: Include demo records.
        :param services: Start services or only the application containers.
                         This option is incompatible will all the other flags.
        """
        steps = []

        if lock:
            # FIXME: Should this params be accepted? sensible defaults?
            steps.extend(PackagesCommands(self.cli_config).lock(pre=True, dev=True))

        if build:
            steps.extend(self.build())

        if services and setup:
            # NOTE: Setup will boot up all service and not bring down
            steps.extend(self.setup(force=True, demo_data=demo_data))
            return steps

        # NOTE: Needed in case there is no setup
        steps.append(
            FunctionStep(
                func=self.docker_helper.start_containers,
                args={"app_only": not services},
                message="Checking if dependencies are locked.",
            )
        )

        return steps
