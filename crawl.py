# pylint: disable=locally-disabled, multiple-statements, line-too-long, missing-module-docstring, no-member, missing-class-docstring, missing-function-docstring

import argparse
from pathlib import Path
from datetime import datetime
import logging
import bz2
from concurrent.futures import as_completed
from urllib.parse import urlparse, parse_qs

try:
    import orjson as json
except ImportError:
    import json

from tqdm.auto import tqdm
import requests
from requests.adapters import HTTPAdapter, Retry
from requests_futures.sessions import FuturesSession
from http import HTTPStatus

logging.basicConfig(filename=f'hamster_{datetime.now()}.log', encoding='utf-8', level=logging.INFO)


def load(file_path: Path):
    with open(file_path, 'rb') as file_handle:
        byte_data = bz2.decompress(file_handle.read())
        return json.loads(byte_data)

def store(data, file_path: Path):
    def remove_keys(data, contains, equals):
        if isinstance(data, dict):
            return {k: remove_keys(v, contains, equals) for k, v in data.items() if not (any(s in k for s in contains) or any(s == k for s in equals))}
        if isinstance(data, list):
            return [remove_keys(i, contains, equals) for i in data]
        return data
    (file_path.parent).mkdir(parents=True, exist_ok=True)
    cleaned_data = remove_keys(data, contains=['url', 'gravatar'], equals=['body', 'href', 'node_id', 'head', 'base', '_links', 'title', 'description'])
    byte_data = json.dumps(cleaned_data)
    byte_data = bz2.compress(byte_data)
    with open(file_path, 'wb') as file_handle:
        file_handle.write(byte_data)


class GitHubAPIError(Exception):
    pass

class GitHubAPI:

    @classmethod
    def read(cls, resp: requests.Response):
        logging.info('HTTP status %i for %s', resp.status_code, resp.url)
        match resp.status_code:
            case HTTPStatus.OK:
                return json.loads(resp.content)
            case HTTPStatus.FORBIDDEN:
                if int(resp.headers.get('X-RateLimit-Remaining', 1)) > 0:
                    return []
                raise GitHubAPIError(f'{resp.status_code} for {resp.url}: {resp.text}')
            case HTTPStatus.NOT_FOUND | HTTPStatus.INTERNAL_SERVER_ERROR: # GitHub API is not bullet-proof
                return []
            case _:
                raise GitHubAPIError(f'{resp.status_code} for {resp.url}: {resp.text}')

    def __init__(self, api_token, out_dir: Path, api_url: str = 'https://api.github.com/', time_out: int = 2*60, num_workers: int = 4):
        if api_url[-1] != '/':
            api_url += '/'
        self.api_url = api_url
        self.num_workers = num_workers
        self.time_out = time_out
        self.out_dir = out_dir

        self.http_session = requests.session()
        self.http_session.headers.update({
            'User-Agent':'collect 1.0',
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {api_token}',
        })

        retries = Retry(total=5,
            connect=5,
            backoff_factor=2,
            status_forcelist=[500, 501, 502, 503, 504],
            raise_on_status=False)

        self.http_session.mount('https://', HTTPAdapter(max_retries=retries))
        self.http_session.mount('http://', HTTPAdapter(max_retries=retries))

    def query(self, endpoint: str, params, progress_desc=None):
        disable_progress = progress_desc is None
        resp = self.http_session.get(self.api_url + endpoint, timeout=self.time_out, params=params)
        result = GitHubAPI.read(resp)

        if 'last' in resp.links:
            parsed_url = urlparse(resp.links['last']['url'])
            captured_value = parse_qs(parsed_url.query)
            last_page = int(captured_value['page'][0])

            with FuturesSession(max_workers=self.num_workers, session=self.http_session) as future_session:
                futures = [future_session.get(self.api_url + endpoint, params=params|{'page': page}) for page in range(2, last_page+1)]
                for future in tqdm(as_completed(futures), disable=disable_progress, total=len(futures), desc=progress_desc):
                    resp = future.result()
                    result += GitHubAPI.read(resp)
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='desc')
    parser.add_argument('api_token', type=str, help='API token')
    parser.add_argument('out_dir', type=Path, help='The output directory for all data')
    parser.add_argument('--api_url', type=str, default='https://api.github.com', help='Specify API URL for GitHub Enterprise')
    parser.add_argument('--disable_cache', default=False, action=argparse.BooleanOptionalAction, help='Disable cache')
    parser.add_argument('--num_workers', type=int, default=1, help='Worker for parallel requests; default 1')
    parser.add_argument('--organization', type=str, help='Specify a single organization')
    args = parser.parse_args()

    gh = GitHubAPI(api_token=args.api_token, out_dir=args.out_dir, api_url=args.api_url, num_workers=args.num_workers)

    if args.organization:
        organizations = [{'login': args.organization}]
    else:
        organizations = []
        org_file_path = args.out_dir / 'organizations.json.bz2'
        if org_file_path.exists() and not args.disable_cache:
            organizations =  load(org_file_path)
        else:
            organizations = gh.query('organizations', params={'per_page': 100}, progress_desc='Collect organizations')
            store(organizations, org_file_path)

    repos = []
    for org_name in tqdm([org['login'] for org in organizations], desc='Collect repos from organizations'):
        repo_file_path = args.out_dir/'orgs'/org_name/'repos.json.bz2'
        if repo_file_path.exists() and not args.disable_cache:
            org_repos = load(repo_file_path)
        else:
            org_repos = gh.query(f'orgs/{org_name}/repos', params={'type': 'all', 'per_page': 100})
            store(org_repos, repo_file_path)
        repos += [tuple(repo['full_name'].split('/')) for repo in org_repos]

    pulls = []
    for owner, name in tqdm(repos, desc='Collect pulls from repositories'):
        if owner == 'guardrail' and name == 'guardrail-tingle-tests':
            continue
        pulls_file_path = args.out_dir/f'repos/{owner}/{name}/pulls.json.bz2'
        if pulls_file_path.exists() and not args.disable_cache:
            repo_pulls = load(pulls_file_path)
        else:
            repo_pulls = gh.query(f'repos/{owner}/{name}/pulls', params={'state': 'all', 'per_page': 100})
            store(repo_pulls, pulls_file_path)
        pulls += [(owner, name, pull['number']) for pull in repo_pulls]

    with FuturesSession(max_workers=args.num_workers, session=gh.http_session) as future_session:
        futures = {}
        for owner, name, pr_number in pulls:
            timeline_file_path = args.out_dir/f'repos/{owner}/{name}/timelines/{pr_number}.json.bz2'
            if not timeline_file_path.exists() or args.disable_cache:
                future = future_session.get(gh.api_url + f'repos/{owner}/{name}/issues/{pr_number}/timeline', params={'per_page': 100})
                futures[future] = (owner, name, pr_number)

        for future in tqdm(as_completed(futures), total=len(futures), desc='Collect timelines for pulls'):
            owner, name, pr_number = futures[future]
            resp = future.result()
            timeline_file_path = args.out_dir/f'repos/{owner}/{name}/timelines/{pr_number}.json.bz2'

            if 'next' in resp.links:
                timeline = gh.query(f'repos/{owner}/{name}/issues/{pr_number}/timeline', params={'per_page': 100})
            else:
                timeline = GitHubAPI.read(resp)
            store(timeline, timeline_file_path)
