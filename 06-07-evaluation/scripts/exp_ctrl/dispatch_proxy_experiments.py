#! /usr/bin/env python3

# Copyright (C) 2021-22 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

# pylint: disable=missing-module-docstring,missing-function-docstring
# pylint: disable=missing-class-docstring

import logging
import os
import re
import sys
import tempfile

from iotlab_controller.experiment import ExperimentError

import riotctrl.ctrl
import riotctrl.shell

try:
    from . import dispatch_load_experiments as dle
except ImportError:
    import dispatch_load_experiments as dle

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2021-22 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

sys.path.append(os.path.join(SCRIPT_PATH, "..", "..", "RIOT", "dist", "pythonlibs"))

# pylint: disable=wrong-import-position,import-error
import riotctrl_shell.netif  # noqa: E402

logger = logging.getLogger(__name__)


class Dispatcher(dle.Dispatcher):
    _RESOLVER_BIND_PORTS = {
        "udp": 5301,
        "dtls": 8531,
        "coap": 8483,
        "coaps": 8484,
        "oscore": 8483,
    }

    def __new__(cls, *args, **kwargs):  # pylint: disable=unused-argument
        cls = super().__new__(cls)  # pylint: disable=self-cls-assignment
        cls._RESOLVER_CONFIG["transports"]["udp"]["port"] = cls._RESOLVER_BIND_PORTS[
            "udp"
        ]
        cls._RESOLVER_CONFIG["transports"]["dtls"]["port"] = cls._RESOLVER_BIND_PORTS[
            "dtls"
        ]
        cls._RESOLVER_CONFIG["transports"]["coap"]["port"] = cls._RESOLVER_BIND_PORTS[
            "coap"
        ]
        return cls

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._border_router_path = os.path.join(
            tempfile.gettempdir(), ".ssh-grenoble-CuI9vNhosI"
        )
        self._dns_resolver_path = os.path.join(
            tempfile.gettempdir(), ".ssh-grenoble-LAgWMJDWuC"
        )

    @staticmethod
    def establish_session(shell):
        # send one query to enforce session / repeat window to be
        # initialized for encrypted communication
        ret = shell.cmd("query example.org inet6 fetch", timeout=60)
        # just look for transmission, response would be printed
        # asynchronously
        if re.search(r"\bt;\d+\s", ret) is None:
            raise ExperimentError("Unable to establish session")

    def pre_run(self, runner, run, ctx, *args, **kwargs):
        # pylint: disable=too-many-locals
        class Shell(riotctrl_shell.netif.Ifconfig):
            # pylint: disable=too-few-public-methods
            pass

        res = super().pre_run(runner, run, ctx, *args, **kwargs)
        if run["args"].get("proxied", False):
            proxy = None
            for i, node in enumerate(runner.nodes):
                if not self.is_proxy(node):
                    continue
                firmware = runner.experiment.firmwares[i]
                ctrl_env = {
                    "BOARD": firmware.board,
                    "IOTLAB_NODE": node.uri,
                }
                ctrl = riotctrl.ctrl.RIOTCtrl(firmware.application_path, ctrl_env)
                ctrl.TERM_STARTED_DELAY = 0.1
                shell = Shell(ctrl)
                with ctrl.run_term(reset=False):
                    if self.verbosity:
                        ctrl.term.logfile = sys.stdout
                    # TODO determine by neighbors  pylint: disable=fixme
                    netifs = riotctrl_shell.netif.IfconfigListParser().parse(
                        shell.ifconfig_list()
                    )
                    ifname = list(netifs)[0]
                    proxy = [
                        a["addr"]
                        for a in netifs[ifname]["ipv6_addrs"]
                        if a["scope"] == "global"
                    ][0]
        for i, node in enumerate(runner.nodes):
            if not self.is_source_node(runner, node):
                continue
            firmware = runner.experiment.firmwares[i]
            ctrl_env = {
                "BOARD": firmware.board,
                "IOTLAB_NODE": node.uri,
            }
            ctrl = riotctrl.ctrl.RIOTCtrl(firmware.application_path, ctrl_env)
            ctrl.TERM_STARTED_DELAY = 0.1
            shell = Shell(ctrl)
            with ctrl.run_term(reset=False):
                if self.verbosity:
                    ctrl.term.logfile = sys.stdout
                if run["args"].get("proxied", False):
                    ret = shell.cmd(f"proxy coap://[{proxy}]/")
                    if f"Configured proxy coap://[{proxy}]/" not in ret:
                        raise ExperimentError(f"Unable to configure proxy {proxy}")
                self.establish_session(shell)
        return res

    def is_proxy(self, node):
        return any(
            node.uri.startswith(p["name"])
            for p in self.descs["globals"]["nodes"]["network"]["proxies"]
        )

    def is_source_node(self, runner, node):
        return not self.is_proxy(node) and super().is_source_node(runner, node)

    def schedule_experiments(self, *args, **kwargs):
        wl_file = os.path.join(
            self.descs["globals"]["firmwares"][-1]["path"], "whitelist.inc"
        )

        with open(wl_file, "w", encoding="utf-8") as whitelist:
            print("#define L2_FILTER_WHITE_LIST { \\", file=whitelist)
            proxy = self.descs["globals"]["nodes"]["network"]["proxies"][-1]
            print(f"    \"{proxy['l2addr']}\", \\", file=whitelist)
            print("}", file=whitelist)
        return super().schedule_experiments(*args, **kwargs)


if __name__ == "__main__":  # pragma: no cover
    dle.main(Dispatcher)
