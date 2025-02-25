# Securing Name Resolution in the IoT: DNS over CoAP

[![DOI][software-badge]][software-doi]
[![Paper on ACM DL][paper-badge]][paper-doi]
[![Build applications][build-badge]][build-workflow]
[![Test scripts][test-badge]][test-workflow]

This repository contains code and documentation to reproduce the experimental results as well as the
raw data results of the paper **"[Securing Name Resolution in the IoT: DNS over CoAP][paper-doi]"**
published in Proceedings of the ACM on Networking (PACMNET).

* Martine S. Lenders, Christian Amsüss, Cenk Gündogan, Marcin Nawrocki, Thomas C. Schmidt, Matthias
  Wählisch. 2023. **Securing Name Resolution in the IoT: DNS over CoAP**, *Proceedings of the ACM on
  Networking (PACMNET)* 1, CoNEXT2, Article 6 (September 2023), 25 pages.
  https://doi.org/10.1145/3609423

##### Abstract
> In this paper, we present the design, implementation, and analysis of DNS over CoAP (DoC), a new
> proposal for secure and privacy-friendly name resolution of constrained IoT devices. We implement
> different design choices of DoC in RIOT, an open-source operating system for the IoT, evaluate
> performance measures in a testbed, compare with DNS over UDP and DNS over DTLS, and validate our
> protocol design based on empirical DNS IoT data. Our findings indicate that plain DoC is on par
> with common DNS solutions for the constrained IoT but significantly outperforms when additional
> standard features of CoAP  are used such as caching. With OSCORE, we can save more than 10 kBytes
> of code memory compared to DTLS, when a CoAP application is already present, and retain the
> end-to-end trust chain with intermediate proxies, while leveraging features such as group
> communication or encrypted en-route caching. We also discuss a compression scheme for very
> restricted links that reduces data by up to 70%.

## Repository structure & Usage

There are two directories of note in this repository:
- [`03-dns-empirical/`](./03-dns-empirical/), which contains the code we used and the results we
gathered for Section 3 _Empirical View on IoT DNS Traffic_, and
- [`05-06-evaluation/`](./05-06-evaluation/), which contains the same for Sections 5 _Comparison of
Low-power DNS Transports_ as well as 6 _Evaluation of Caching for DoC_.

The third, [`.github/workflows/`](./.github/workflows/), configures the [GitHub CI] for regular
testing of the RIOT applications and Python scripts of this repository

The following graphic gives a rough overview over the workflow of the artifact:

<figure>
<p align="center">
<img width="100%" src="artifacts-overview.svg" />
</p>
<figcaption>
  <div align="center">
  Overview over the workflow in this artifact.
  </div>
</figcaption>
</figure>

### [`03-dns-empirical/`](./03-dns-empirical/)
This directory contains the code we used and the results we gathered for Section 3 _Empirical View
on IoT DNS Traffic_. We recommend reading the [documentation](./03-dns-empirical/README.md) for this
directory first. For the quickest start, however, given that all requirements are installed and you
provided the base data sets we used in our experiments (see subdirectory
[collect](./03-dns-empirical/collect/README.md) for more details), run:

```sh
# 1. 03-dns-empirical
cd 03-dns-empirical

# 1.1. Gather DNS data sets (only runnable if you have access to IXP dumps)
LOGDIR=${YOUR_IXP_DUMPS} TS_START=${START_ISO_DATE} TS_END=${END_ISO_DATE} \
    ./collect/run_parallel_ixp_dns.sh          # generate ./results/ixp-data-sets/dns_packets_ixp_2022_week.csv.gz

# 1.2. Prepare DNS data sets
for iot_dataset in ${IOT_DATASETS}; do
    ./collect/scan_iot_data.py ${iot_dataset}  # Scan IoT Dataset PCAPs
done

# reformat to format corresponding the IoT Datasets
./collect/reformat_dns_week_2022_2.py ./results/ixp-data-set/dns_packets_ixp_2022_week.csv.gz

# 3. Analyze
# Generate plots for all filters and dataset combinations
./plot/plot_iot_data_all.sh
```

**Attention:** These scripts may run for a while.

The CSVs and results will be updated accordingly in
[`03-dns-empirical/results/`](./03-dns-empirical/results/).

### [`05-06-evaluation/`](./05-06-evaluation/)

This directory contains the code we used and the results we gathered for Sections 5 _Comparison of
Low-power DNS Transports_ as well as 6 _Evaluation of Caching for DoC_. We recommend reading the
[documentation](./05-06-evaluation/README.md) for this directory first. For the quickest start,
however, given that all requirements are installed, run:

```sh
# 2. 05-06-evaluation
cd 05-06-evaluation/scripts

# Do experiments for Section 5
# 2.1 Prepare experiments
./exp_ctrl/create_comp_descs.py     # create descs.yaml for DNS transport comparison
# 2.2 Run experiments
./exp_ctrl/setup_exp.sh comp        # run experiments for DNS transport comparison (opens a TMUX session)
# 2.3. Treat logs
./plots/parse_comp_results.py       # parse logs into easier to process CSVs

# Do experiments for Section 6
# 2.1 Prepare experiments
./exp_ctrl/create_max_age_descs.py  # create descs.yaml for caching evaluation
# 2.2 Run experiments
./exp_ctrl/setup_exp.sh max_age     # run experiments for caching evaluation (opens a TMUX session)
# 2.3. Treat logs
./plots/parse_max_age_results.py    # parse logs into easier to process CSVs
#   (the graphic is simplified here, this step does not show up)
./plots/parse_max_age_link_util.py  # parse PCAPs into link utilization CSV (may run for a while)

# 2.5 Get memory profiles
# Build requester app for IoT-LAB M3 in different configuration and collect object sizes
./plots/collect_build_sizes.py
# Build requester app and Quant RIOT app for ESP32 in different configuration and collect object sizes
./plots/collect_esp32_build_sizes.py

# 3. Analyze
./plots/plot_all.sh
```

The logs, CSVs, and results will be updated accordingly in
[`05-06-evaluation/results/`](./05-06-evaluation/results/).

## License

The program code in this repository is subject to the terms and conditions of the GNU Lesser General
Public License v2.1. See the file [LICENSE](./LICENSE) for more details.

The experiments result files and plots are licensed under a [Creative
Commons Attribution 4.0 International License][CC BY 4.0]. See the LICENSE files in
[`03-dns-empirical/results`](./03-dns-empirical/results/LICENSE) and
[`05-06-evaluation/results`](./05-06-evaluation/results/LICENSE), respectively.

[paper-badge]: https://img.shields.io/badge/Paper-ACM%20DL-green
[paper-doi]: https://doi.org/10.1145/3609423
[software-badge]: https://zenodo.org/badge/DOI/10.5281/zenodo.8190924.svg
[software-doi]: https://doi.org/10.5281/zenodo.8190924
[build-badge]: https://github.com/anr-bmbf-pivot/doc-eval/actions/workflows/build-apps.yml/badge.svg
[build-workflow]: https://github.com/anr-bmbf-pivot/doc-eval/actions/workflows/build-apps.yml
[test-badge]: https://github.com/anr-bmbf-pivot/doc-eval/actions/workflows/test-scripts.yml/badge.svg
[test-workflow]: https://github.com/anr-bmbf-pivot/doc-eval/actions/workflows/test-scripts.yml
[GitHub CI]: https://docs.github.com/actions
[CC BY 4.0]: https://creativecommons.org/licenses/by/4.0
