#! /usr/bin/env python3

# Copyright (C) 2021-22 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import ast
import logging
import re
import os

import numpy

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2021-22 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get(
    "DATA_PATH", os.path.join(SCRIPT_PATH, "..", "..", "results")
)
OUTPUT_FORMATS = ["pdf", "svg"]
FILENAME_PATTERN_FMT = (
    r"doc-eval-{exp_type}(-{node_num})?(-{link_layer})?(-{max_age_config})?"
    r"-{transport}(-{method})?(-dc{dns_cache})?(-ccc{client_coap_cache})?"
    r"(-proxied{proxied})?(-b{blocksize})?-{delay_time}"
    r"-{delay_queries}-{queries}x{avg_queries_per_sec}(-{record})?-(?P<exp_id>\d+)"
    r"-(?P<timestamp>\d+)(?P<border_router>\.border-router)?"
)
CSV_NAME_PATTERN_FMT = rf"{FILENAME_PATTERN_FMT}\.{{csv_type}}\.csv"
CSV_EXT_FILTER = ["times.csv", "stats.csv"]
LINK_LAYER_DEFAULT = "ieee802154"
COAP_METHOD_DEFAULT = "fetch"
COAP_BLOCKSIZE_DEFAULT = None
QUERIES_DEFAULT = 50
AVG_QUERIES_PER_SEC_DEFAULT = 10
RECORD_TYPE_DEFAULT = "AAAA"
PROXIED_DEFAULT = 0
RUNS = 10
EXP_TYPES = [
    "baseline",
    "comp",
    "max_age",
]
LINK_LAYERS = [
    "ieee802154",
    "ble",
]
TRANSPORTS = [
    "oscore",
    "coaps",
    "coap",
    "dtls",
    "udp",
]
AVG_QUERIES_PER_SEC = numpy.arange(5, 10.5, step=5)
COAP_TRANSPORTS = {
    "coap",
    "coaps",
    "oscore",
}
COAP_METHODS = [
    "fetch",
    "get",
    "post",
]
DNS_CACHE = [False, True]
CLIENT_COAP_CACHE = [True, False]
COAP_BLOCKSIZE = [
    16,
    32,
    64,
    None,
]
PROXIED = [
    0,
    1,
]
PROXIED_READABLE = {
    0: "w/o proxy",
    1: "w/ proxy",
}
RECORD_TYPES = [
    "AAAA",
    "A",
]
RESPONSE_DELAYS = [
    (None, None),
    (1.0, 25),
]

BLOCKWISE_READABLE = {
    None: "No blockwise",
    16: "16 bytes",
    32: "32 bytes",
    64: "64 bytes",
}
BLOCKWISE_STYLE = {
    None: {},
    16: {"marker": "o", "markevery": 600, "markersize": 2},
    32: {"marker": "x", "markevery": 600, "markersize": 2},
    64: {"marker": "*", "markevery": 600, "markersize": 2},
}
MAX_AGE_CONFIGS = [
    "dohlike",
    "eolttls",
]
MAX_AGE_CONFIG_READABLE = {
    "dohlike": "DoH-like",
    "eolttls": "Adapt TTLs",
}
MAX_AGE_CONFIG_STYLE = {
    "dohlike": {},
    "eolttls": {"marker": "+", "markevery": 200, "markersize": 2, "linestyle": ":"},
}


class TransportsReadable:  # pylint: disable=too-few-public-methods
    class TransportReadable:  # pylint: disable=too-few-public-methods
        class MethodReadable:  # pylint: disable=too-few-public-methods
            METHODS_READABLE = {
                "fetch": "FETCH",
                "get": "GET",
                "post": "POST",
            }

            def __init__(self, transport, method=None):
                self.transport = transport
                self.method = method

            def __str__(self):
                if self.method is None:
                    return str(self.transport)
                return f"{self.transport} ({self.METHODS_READABLE[self.method]})"

        TRANSPORTS_READABLE = {
            "coap": "CoAP",
            "coaps": "CoAPSv1.2",
            "oscore": "OSCORE",
            "dtls": "DTLSv1.2",
            "udp": "UDP",
        }

        def __init__(self, transport):
            self.transport = transport

        def __getitem__(self, method):
            if self.transport not in COAP_TRANSPORTS:
                return self.MethodReadable(self)
            elif method is None:
                method = "fetch"
            return self.MethodReadable(self, method)

        def __str__(self):
            return self.TRANSPORTS_READABLE[self.transport]

    def __getitem__(self, transport):
        return self.TransportReadable(transport)


class TransportsStyle(dict):
    TRANSPORTS_STYLE = {
        "coap": {"color": "C4"},
        "coaps": {"color": "C3"},
        "oscore": {"color": "C2"},
        "dtls": {"color": "C1"},
        "udp": {"color": "C0"},
    }

    class TransportStyle(dict):
        METHODS_STYLE = {
            "fetch": {"linestyle": "-"},
            "get": {"linestyle": ":"},
            "post": {"linestyle": "--"},
        }

        def __init__(self, transport_style, transport, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.update(transport_style)
            self.transport = transport

        def __getitem__(self, method):
            if method is None:
                return self
            if (
                self.transport not in COAP_TRANSPORTS
                or method not in self.METHODS_STYLE
            ):
                return super().__getitem__(method)
            return dict(**self, **self.METHODS_STYLE[method])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for transport, style in self.TRANSPORTS_STYLE.items():
            self[transport] = style

    def __getitem__(self, transport):
        return self.TransportStyle(super().__getitem__(transport), transport)


TRANSPORTS_READABLE = TransportsReadable()
METHODS_READABLE = TransportsReadable.TransportReadable.MethodReadable.METHODS_READABLE
TRANSPORTS_STYLE = TransportsStyle()


def get_files(  # pylint: disable=too-many-arguments
    exp_type,
    transport,
    method=None,
    delay_time=None,
    delay_queries=None,
    queries=QUERIES_DEFAULT,
    avg_queries_per_sec=AVG_QUERIES_PER_SEC_DEFAULT,
    record="AAAA",
    csv_type="times",
    link_layer=LINK_LAYER_DEFAULT,
    blocksize=None,
    proxied=None,
    max_age_config=None,
    dns_cache=None,
    client_coap_cache=None,
    node_num=None,
):
    avg_queries_per_sec = round(float(avg_queries_per_sec), 1)
    exp_dict = {
        "exp_type": exp_type,
        "node_num": f"(?P<node_num>{node_num})",
        "link_layer": f"(?P<link_layer>{link_layer})",
        "transport": transport,
        "delay_time": delay_time,
        "delay_queries": delay_queries,
        "method": f"(?P<method>{method})",
        "blocksize": f"(?P<blocksize>{blocksize})",
        "proxied": f"(?P<proxied>{proxied})",
        "queries": queries,
        "avg_queries_per_sec": avg_queries_per_sec,
        "record": f"(?P<record>{record})",
        "csv_type": csv_type,
        "max_age_config": f"(?P<max_age_config>{max_age_config})",
        "dns_cache": f"(?P<dns_cache>{dns_cache})",
        "client_coap_cache": f"(?P<client_coap_cache>{client_coap_cache})",
    }
    pattern = CSV_NAME_PATTERN_FMT.format(**exp_dict)
    pattern_c = re.compile(pattern)
    filenames = filter(
        lambda x: x[0] is not None and (x[0]["record"] is not None or record == "AAAA"),
        map(
            lambda f: (pattern_c.match(f), os.path.join(DATA_PATH, f)),
            os.listdir(DATA_PATH),
        ),
    )
    filenames = sorted(filenames, key=lambda x: int(x[0]["timestamp"]))
    res = []
    for match, filename in filenames:
        if match["node_num"] is None and node_num is not None:
            continue  # pragma: no cover
        if match["link_layer"] is None and link_layer != LINK_LAYER_DEFAULT:
            continue  # pragma: no cover
        if match["record"] is None and record != RECORD_TYPE_DEFAULT:
            continue  # pragma: no cover
        if match["dns_cache"] is None and dns_cache:
            continue  # pragma: no cover
        if match["client_coap_cache"] is None and (
            client_coap_cache is not None and not client_coap_cache
        ):
            continue  # pragma: no cover
        if (
            transport in COAP_TRANSPORTS
            and match["method"] is None
            and method != COAP_METHOD_DEFAULT
        ):
            continue  # pragma: no cover
        if (
            transport in COAP_TRANSPORTS
            and match["blocksize"] is None
            and blocksize != COAP_BLOCKSIZE_DEFAULT
        ):
            continue
        if max_age_config is not None and match["max_age_config"] is None:
            continue  # pragma: no cover
        if any(  # pragma: no cover
            filename.endswith(ext_filter) for ext_filter in CSV_EXT_FILTER
        ):
            res.append((match, filename))
    if len(res) != RUNS:
        logging.warning(
            "doc-eval-%s%s-%s%s-%s%s%s%s%s%s-%s-%s-%dx%.1f-%s"
            " %shas %d of %d expected runs",
            exp_dict["exp_type"],
            f"-{exp_dict['node_num']}" if exp_dict["node_num"] is not None else "",
            exp_dict["link_layer"],
            f"-{max_age_config}" if max_age_config is not None else "",
            exp_dict["transport"],
            f"-{method}" if method is not None else "",
            f"-dc{dns_cache:d}" if dns_cache is not None else "",
            f"-ccc{client_coap_cache:d}" if client_coap_cache is not None else "",
            f"-b{blocksize}" if blocksize is not None else "",
            f"-proxied{proxied}" if proxied is not None else "",
            exp_dict["delay_time"],
            exp_dict["delay_queries"],
            exp_dict["queries"],
            exp_dict["avg_queries_per_sec"],
            record,
            "only " if len(res) < RUNS else "",
            len(res),
            RUNS,
        )
    return res


# def reject_outliers(data, m=2):  # pylint: disable=invalid-name
#     # pylint: disable=invalid-name
#     d = numpy.abs(data - numpy.median(data))
#     mdev = numpy.median(d)
#     s = d / mdev if mdev else 0.0
#     data = numpy.array(data)
#     return data[s < m]


def _normalize_cache_hits(row, base_time):
    for key in ["cache_hits", "client_cache_hits"]:
        try:
            if key not in row:
                continue
            try:
                row[key] = ast.literal_eval(row[key])
            except SyntaxError:
                if row[key] == "":
                    row[key] = []
                else:
                    logging.error(
                        "Unable to parse cache_hits in row %s "
                        "for query at timestamp %f",
                        row,
                        row["query_time"] + base_time,
                    )
                    row[key] = []
            for i, cache_hit in enumerate(row[key]):
                try:
                    row[key][i] = float(cache_hit) - base_time
                except ValueError:
                    row[key][i] = float("nan")
        except ValueError:
            row[key] = []


def normalize_times_and_ids(row, base_id=None, base_time=None):
    if base_id is None:
        base_id = int(row["id"])
    if base_time is None:
        base_time = float(row["query_time"])
    row["id"] = int(row["id"]) - base_id
    row["query_time"] = float(row["query_time"]) - base_time
    if row.get("response_time"):
        row["response_time"] = float(row["response_time"]) - base_time
    try:
        try:
            row["transmissions"] = ast.literal_eval(row.get("transmissions", "[]"))
        except SyntaxError:
            if row["transmissions"] == "":
                row["transmissions"] = []
            else:
                logging.error(
                    "Unable to parse transmissions in row %s for query at timestamp %f",
                    row,
                    row["query_time"] + base_time,
                )
                row["transmissions"] = []
        for i, transmission in enumerate(row["transmissions"]):
            try:
                row["transmissions"][i] = float(transmission) - base_time
            except ValueError:
                row["transmissions"][i] = float("nan")
        _normalize_cache_hits(row, base_time)
    except ValueError:
        row["transmissions"] = []
    if row.get("unauth_time"):
        row["unauth_time"] = float(row["unauth_time"]) - base_time
    return base_id, base_time
