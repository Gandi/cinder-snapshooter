"""
Copyright 2021 Gandi SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
import logging

import keystoneauth1.exceptions
import pytest
import structlog.stdlib

import cinder_snapshooter.utils
import fixtures


@pytest.mark.parametrize(
    "value, result",
    [
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("yes", True),
        ("wrong", False),
        ("FALSE", False),
        ("no", False),
        ("random string", False),
    ],
)
def test_str2bool(value, result):
    assert cinder_snapshooter.utils.str2bool(value) == result


@pytest.mark.parametrize("devel", [True, False])
@pytest.mark.parametrize("verbose", [0, 1, 2, 3, 4])
def test_setup_logging(mocker, faker, devel, verbose):
    mocker.patch("structlog.stdlib.ProcessorFormatter")
    mocker.patch("logging.getLogger")
    loggers = {}

    def get_logger(name=""):
        if name not in loggers:
            loggers[name] = mocker.MagicMock()
        return loggers[name]

    logging.getLogger.side_effect = get_logger
    args = argparse.Namespace(verbose=verbose, devel=devel)
    cinder_snapshooter.utils.setup_logging(args)

    if devel:
        processor_class = structlog.dev.ConsoleRenderer
    else:
        processor_class = structlog.processors.JSONRenderer

    assert structlog.stdlib.ProcessorFormatter.call_count == 1
    assert isinstance(
        structlog.stdlib.ProcessorFormatter.call_args[1]["processors"][-1],
        processor_class,
    )
    loggers[""].setLevel.assert_called_once_with(
        logging.INFO if verbose == 0 else logging.DEBUG
    )
    info_loggers = ["keystoneauth", "urllib3", "stevedore"]
    debug_loggers = []
    if verbose >= 2:
        debug_loggers += ["stevedore", "openstack.config", "openstack.fnmatch"]
        info_loggers.pop()
    if verbose >= 3:
        debug_loggers += ["keystoneauth", "urllib3"]
        info_loggers = []
    if verbose >= 4:
        debug_loggers += ["openstack.iterate_timeout"]

    for logger in info_loggers:
        assert loggers[logger].setLevel.call_args == mocker.call(logging.INFO)
    for logger in debug_loggers:
        assert loggers[logger].setLevel.call_args == mocker.call(logging.DEBUG)


def test_available_projects(mocker, faker):
    os_client = mocker.MagicMock()
    trusts = [fixtures.FakeTrust(id=faker.uuid4(), project_id=faker.uuid4())]
    projects = [fixtures.FakeProject(id=faker.uuid4(), name=faker.domain_name())]
    os_client.identity.trusts.return_value = trusts
    os_client.identity.user_projects.return_value = projects
    assert list(cinder_snapshooter.utils.available_projects(os_client)) == [
        (trust.id, trust.project_id) for trust in trusts
    ] + [(None, project.id) for project in projects]


def test_run_on_all_projects(mocker, faker, log):
    mocker.patch("cinder_snapshooter.utils.available_projects")
    projects = [
        (None, faker.uuid4()),
        (faker.uuid4(), faker.uuid4()),
    ]
    cinder_snapshooter.utils.available_projects.return_value = projects

    def connect_as(**kwargs):
        return kwargs

    os_client = mocker.MagicMock()
    os_client.connect_as.side_effect = connect_as

    process_function = mocker.MagicMock()
    process_function_args = (("yet another argument",), {"some_kwargs": True})
    process_function_rv = [faker.boolean() for _ in projects]
    process_function.side_effect = process_function_rv

    rv = cinder_snapshooter.utils.run_on_all_projects(
        os_client,
        process_function,
        *process_function_args[0],
        **process_function_args[1],
    )

    assert rv == process_function_rv
    assert os_client.connect_as.call_args_list == [
        mocker.call(project_id=projects[0][1]),
        mocker.call(trust_id=projects[1][0]),
    ]
    assert process_function.call_args_list == [
        mocker.call(
            {"project_id": projects[0][1]},
            *process_function_args[0],
            **process_function_args[1],
        ),
        mocker.call(
            {"trust_id": projects[1][0]},
            *process_function_args[0],
            **process_function_args[1],
        ),
    ]


@pytest.mark.parametrize("return_code", [401, 403])
def test_run_on_all_project_raising(mocker, faker, log, return_code):
    mocker.patch("cinder_snapshooter.utils.available_projects")

    projects = [
        (None, faker.uuid4()),
        (faker.uuid4(), faker.uuid4()),
    ]
    cinder_snapshooter.utils.available_projects.return_value = projects

    def connect_as(**kwargs):
        return kwargs

    os_client = mocker.MagicMock()
    os_client.connect_as.side_effect = connect_as

    process_function = mocker.MagicMock()
    process_function.side_effect = keystoneauth1.exceptions.HTTPClientError(
        http_status=return_code,
    )

    if return_code == 403:
        rv = cinder_snapshooter.utils.run_on_all_projects(
            os_client,
            process_function,
        )
        assert rv == []
        assert os_client.connect_as.call_args_list == [
            mocker.call(project_id=projects[0][1]),
            mocker.call(trust_id=projects[1][0]),
        ]
        assert process_function.call_args_list == [
            mocker.call(
                {"project_id": projects[0][1]},
            ),
            mocker.call(
                {"trust_id": projects[1][0]},
            ),
        ]
    else:
        with pytest.raises(keystoneauth1.exceptions.HTTPClientError):
            cinder_snapshooter.utils.run_on_all_projects(
                os_client,
                process_function,
            )
