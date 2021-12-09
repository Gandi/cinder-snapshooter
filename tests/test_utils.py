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

import pytest
import structlog.stdlib

import cinder_snapshooter.utils


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
