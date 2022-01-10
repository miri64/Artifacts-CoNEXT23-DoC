#! /usr/bin/env python
#
# Copyright (C) 2021 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import argparse
import csv
import math
import os

import matplotlib.lines
import matplotlib.pyplot
import numpy

try:
    from . import plot_common as pc
except ImportError:
    import plot_common as pc

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2021 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"


def cdf(ttcs):
    bins = (
        numpy.arange(
            numpy.floor(ttcs.min() * 100),
            numpy.floor(ttcs.max() * 100),
        )
        / 100
    )
    hist, x = numpy.histogram(ttcs, bins=bins, density=1)
    if len(x) < 2:
        return numpy.array([]), numpy.array([])
    dx = x[1] - x[0]
    return x[1:], numpy.cumsum(hist) * dx


def process_data(
    transport,
    method=None,
    delay_time=None,
    delay_queries=None,
    queries=pc.QUERIES_DEFAULT,
    avg_queries_per_sec=pc.AVG_QUERIES_PER_SEC_DEFAULT,
    record=pc.RECORD_TYPE_DEFAULT,
    link_layer=pc.LINK_LAYER_DEFAULT,
):
    files = pc.get_files(
        "load",
        transport,
        method,
        delay_time,
        delay_queries,
        queries,
        avg_queries_per_sec,
        record,
        link_layer=link_layer,
        blocksize=blocksize,
    )
    res = []
    for match, filename in files[-pc.RUNS :]:
        filename = os.path.join(pc.DATA_PATH, filename)
        with open(filename, encoding="utf-8") as timesfile:
            reader = csv.DictReader(timesfile, delimiter=";")
            base_id = None
            base_time = None
            for row in reader:
                base_id, base_time = pc.normalize_times_and_ids(row, base_id, base_time)
                if row.get("response_time"):
                    times = (row["response_time"] - row["query_time"],)
                    res.append(times)
    if res:
        return cdf(numpy.array(res))
    return numpy.array([]), numpy.array([])


def label_plots(axins, link_layer, delay_time):
    matplotlib.pyplot.xlabel("Resolution time [s]")
    matplotlib.pyplot.xlim((0, 25))
    matplotlib.pyplot.xticks(numpy.arange(0, 26, step=5))
    matplotlib.pyplot.ylabel("CDF")
    matplotlib.pyplot.ylim((0, 1))
    matplotlib.pyplot.grid(True, linestyle=":")
    if link_layer == "ble" or delay_time == 5:
        axins.set_xlim((0, 2))
        axins.set_ylim((0.95, 1))
        axins.set_xticks(numpy.arange(0, 2.5, step=0.5))
        axins.set_yticks(numpy.arange(0.95, 1.0, step=0.01))
    else:
        axins.set_xlim((0, 9.5))
        axins.set_ylim((0.83, 1))
        axins.set_xticks(numpy.arange(0, 9.5, step=2))
        axins.set_yticks(numpy.arange(0.85, 1.04, step=0.05))
    axins.yaxis.set_label_position("right")
    axins.yaxis.tick_right()
    axins.grid(True, linestyle=":")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "link_layer",
        nargs="?",
        default=pc.LINK_LAYER_DEFAULT,
        choices=pc.LINK_LAYERS,
        help=f"Link layer to plot (default={pc.LINK_LAYER_DEFAULT})",
    )
    args = parser.parse_args()
    for record in pc.RECORD_TYPES:
        for time, queries in pc.RESPONSE_DELAYS:
            for avg_queries_per_sec in pc.AVG_QUERIES_PER_SEC:
                plots_contained = 0
                matplotlib.pyplot.figure(figsize=(4, 9 / 4))
                axins = matplotlib.pyplot.gca().inset_axes([0.4, 0.15, 0.45, 0.75])
                methods_plotted = set()
                transports_plotted = set()
                for transport in reversed(pc.TRANSPORTS):
                    for m, method in enumerate(pc.COAP_METHODS):
                        if transport not in pc.COAP_TRANSPORTS:
                            if m > 0:
                                continue
                            method = None
                        x, y = process_data(
                            transport,
                            method,
                            time,
                            queries,
                            avg_queries_per_sec=avg_queries_per_sec,
                            record=record,
                            link_layer=args.link_layer,
                        )
                        if len(x) == 0 or len(y) == 0:
                            continue
                        transports_plotted.add(transport)
                        methods_plotted.add(method)
                        matplotlib.pyplot.plot(
                            x,
                            y,
                            label=pc.TRANSPORTS_READABLE[transport][method],
                            **pc.TRANSPORTS_STYLE[transport][method],
                        )
                        axins.plot(
                            x,
                            y,
                            label=pc.TRANSPORTS_READABLE[transport][method],
                            **pc.TRANSPORTS_STYLE[transport][method],
                        )
                        plots_contained += 1
                        print(x.max())
                        label_plots(axins, args.link_layer, time)
                if plots_contained:
                    transport_readable = pc.TransportsReadable.TransportReadable
                    transport_handles = [
                        matplotlib.lines.Line2D(
                            [0],
                            [0],
                            label=transport_readable.TRANSPORTS_READABLE[transport],
                            **pc.TRANSPORTS_STYLE[transport],
                        )
                        for transport in reversed(pc.TRANSPORTS)
                        if transport in transports_plotted
                    ]
                    ax = matplotlib.pyplot.gca()
                    ax.indicate_inset_zoom(axins, edgecolor="black")
                    transport_legend = matplotlib.pyplot.legend(
                        handles=transport_handles,
                        loc="upper center",
                        title="DNS Transports",
                        ncol=math.ceil(len(pc.TRANSPORTS) / 2),
                        bbox_to_anchor=(0.5, 1.6),
                    )
                    ax.add_artist(transport_legend)
                    if methods_plotted != {"fetch"}:
                        method_readable = transport_readable.MethodReadable
                        method_handles = [
                            matplotlib.lines.Line2D(
                                [0],
                                [0],
                                label=method_readable.METHODS_READABLE[method],
                                color="black",
                                **pc.TransportsStyle.TransportStyle.METHODS_STYLE[
                                    method
                                ],
                            )
                            for method in reversed(pc.COAP_METHODS)
                            if method in methods_plotted
                        ]
                        method_legend = matplotlib.pyplot.legend(
                            handles=method_handles,
                            loc="lower left",
                            title="CoAP Method",
                        )
                        ax.add_artist(method_legend)
                    matplotlib.pyplot.tight_layout()
                    for ext in ["pgf", "svg"]:
                        matplotlib.pyplot.savefig(
                            os.path.join(
                                pc.DATA_PATH,
                                f"doc-eval-load-{args.link_layer}-cdf-{time}-{queries}-"
                                f"{avg_queries_per_sec}-{record}.{ext}",
                            ),
                            bbox_inches="tight",
                        )
                matplotlib.pyplot.close()


if __name__ == "__main__":
    main()
