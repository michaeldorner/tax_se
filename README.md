# Taxing Collaborative Software Engineering

[![GitHub](https://img.shields.io/github/license/michaeldorner/tax_se)](./LICENSE)

Replication package for our work on "Taxing Collaborative Software Engineering"

## Requirements

```
python3 -m pip install -r requirements.txt
```

For a faster loading, we recommend to optionally install [`orjson`](https://github.com/ijl/orjson) via pip:
```
python3 -m pip install orjson
```

## How to run

### Step 1: Crawl 

First, we collect all timelines from all pull requests at a GitHub instance. The crawler requires an `<api_token>` from GitHub and an `<out_dir>` where the results are stored into:
```
python3 crawl.py <api_token> <out_dir>
```
The crawler also provides options
- `--api_url` for the GitHub instance URL (default: `https://api.github.com`)
- `--disable_cache` for disable caching (for larger instances not recommended)
- `--num_workers` for parallel processes (default: 1)
- `--organization` for limiting to one organization (helpful for organizations hosted on github.com)

To list all options in detail, run
```
python3 crawp.py --h
```

### Step 2: Model pull requests as cross-border communication channels

For this step, you will need a mapping of users and countries. This can be either a `dict` for a static mapping (does not capture changes in the users' location over time) or a dataframe for time-dependent mapping as data frame monthly sampled (captures changes in the users' location over time). 

Run `notebook.ipynb`. Look out for the instructions as inline comments. 

## License

Copyright © 2023 Michael Dorner

This work is licensed under [MIT license](LICENSE).

