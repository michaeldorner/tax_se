# Taxing Collaborative Software Engineering

[![GitHub](https://img.shields.io/github/license/michaeldorner/tax_se)](./LICENSE)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/cca06dbbf55946b883129195e855ecd1)](https://app.codacy.com/gh/michaeldorner/tax_se/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

Replication package for our work on "Taxing Collaborative Software Engineering"

## Requirements

This replication package requires Python 3.10 or higher. Install the dependencies via

```
python3 -m pip install -r requirements.txt
```

For a faster loading, we recommend to optionally install [`orjson`](https://github.com/ijl/orjson) via pip:
```
python3 -m pip install orjson
```

## How to run

### Step 1: Crawl 

First, we collect all timelines from all pull requests at a GitHub instance. [`crawler.py`](crawler.py) requires an [`<api_token>` for your GitHub instance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) and an `<out_dir>` where the results are stored into:
```
python3 crawl.py <api_token> <out_dir>
```
[`crawler.py`](crawler.py also provides the following optional command line arguments:
- `--api_url` for the GitHub instance URL (default: `https://api.github.com`)
- `--disable_cache` for disable caching (for larger instances not recommended)
- `--num_workers` for parallel processes (default: 1)
- `--organization` for limiting to one organization (helpful for organizations hosted on github.com)

To list all options in detail, run
```
python3 crawl.py --h
```

### Step 2: Model pull requests as cross-border communication channels

For this step, you will need 
1) the directory of the previously collected data and
2) a mapping of users and countries. This can be either a `dict` for a static mapping (does not capture changes in the users' location over time) or a dataframe for time-dependent mapping as data frame monthly sampled (captures changes in the users' location over time). 

Run [`notebook.ipynb`](notebook.ipynb). Look out for the instructions as inline comments. 

## License

Copyright © 2023 Michael Dorner

This work is licensed under [MIT license](LICENSE).

