import argparse
import concurrent.futures
import os
from time import sleep
from urllib.parse import quote

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15"
}


def parse_args():
    parser = argparse.ArgumentParser(description='Clone from the https://anonymous.4open.science')
    parser.add_argument('--dir', type=str, default='master', help='save dir')
    parser.add_argument('--url', type=str,
                        help='target anonymous github link eg., https://anonymous.4open.science/r/840c8c57-3c32-451e-bf12-0e20be300389/')
    parser.add_argument('--max-conns', type=int, default=4, help='max connections number')
    return parser.parse_args()


def request_with_retry(url, params=None, max_retry=8, timeout=60):
    last_exc = None
    for i in range(max_retry):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
            if resp.status_code == 429:
                retry_after = resp.headers.get('Retry-After')
                sleep(float(retry_after) if retry_after else min(2 ** i, 10))
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            sleep(min(2 ** i, 10))
    raise last_exc


def fetch_file_list(repo_name):
    list_url = f"https://anonymous.4open.science/api/repo/{repo_name}/files/"
    pending_dirs = ['']
    visited_dirs = set()
    files = []

    while pending_dirs:
        current_dir = pending_dirs.pop()
        if current_dir in visited_dirs:
            continue
        visited_dirs.add(current_dir)

        params = {'path': current_dir} if current_dir else None
        resp = request_with_retry(list_url, params=params)

        for entry in resp.json():
            entry_path = os.path.join(entry.get('path', ''), entry['name']).replace('\\', '/')
            if 'size' in entry:
                files.append((entry_path, entry['size']))
            else:
                pending_dirs.append(entry_path)

    return files


def req_url(dl_file, max_retry=8):
    url, save_path, expected_size = dl_file
    save_dir = os.path.dirname(save_path)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    if os.path.exists(save_path) and os.path.getsize(save_path) == expected_size:
        return 'skipped'

    last_exc = None
    for i in range(max_retry):
        try:
            resp = request_with_retry(url, max_retry=max_retry)
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            if os.path.getsize(save_path) != expected_size:
                raise IOError(f'size mismatch: expected {expected_size}, got {os.path.getsize(save_path)}')
            return 'downloaded'
        except Exception as e:
            last_exc = e
            print('file request exception (retry {}): {} - {}'.format(i, e, save_path))
            sleep(min(2 ** i, 10))

    raise last_exc


if __name__ == '__main__':
    args = parse_args()
    assert args.url, '\nPlese specifipy your target anonymous github link, \n e.g:    ' \
            + 'python download.py --target https://anonymous.4open.science/r/840c8c57-3c32-451e-bf12-0e20be300389/'

    url = args.url
    name = url.split('/')[-2]
    max_conns = args.max_conns

    print('[*] cloning project:' + name)
    file_list = fetch_file_list(name)

    print('[*] downloading files:')

    dl_url = f"https://anonymous.4open.science/api/repo/{name}/file/"
    files = []
    out = []
    for file_path, expected_size in file_list:
        save_path = os.path.join(args.dir, file_path)
        file_url = dl_url + quote(file_path, safe='/')
        files.append((file_url, save_path, expected_size))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_conns) as executor:
        future_to_url = [executor.submit(req_url, dl_file) for dl_file in files]
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
            except Exception as exc:
                data = str(type(exc))
            finally:
                out.append(data)
                print(str(len(out)), end='\r')

    print('[*] files saved to:' + args.dir)
