# clone_anonymous_github

Download repositories from `anonymous.4open.science`.

This fork updates the original script so it works with the current anonymous.4open.science API behavior, especially for repositories with nested directories and many files.

## What this fork fixes

Compared with the earlier script version, this fork now:

- recursively traverses repository directories using the current `files/?path=...` API pattern
- retries failed requests when the service returns transient network errors
- backs off and retries when the service returns `429 Too Many Requests`
- URL-encodes file paths before downloading
- skips files that are already present locally with the expected size
- verifies downloaded file size to reduce the chance of keeping partial files
- uses a lower default concurrency for better stability on large repositories

## Installation

```bash
git clone https://github.com/wanweilin/clone_anonymous_github.git
cd clone_anonymous_github
pip install requests
```

## Basic usage

```bash
python download.py --url https://anonymous.4open.science/r/<repo-id>/ --dir savepath/
```

Example:

```bash
python download.py \
  --url https://anonymous.4open.science/r/TritonDFT-43C7/ \
  --dir download/TritonDFT-43C7
```

Important:

- keep the trailing slash at the end of `--url`
- use a writable output directory for `--dir`
- if the remote service is unstable, rerun the same command and the script will skip files that were already downloaded successfully

## Arguments

- `--url`: target anonymous repository URL, for example `https://anonymous.4open.science/r/TritonDFT-43C7/`
- `--dir`: local output directory
- `--max-conns`: maximum concurrent download workers, default `4`

Example with an explicit worker count:

```bash
python download.py \
  --url https://anonymous.4open.science/r/TritonDFT-43C7/ \
  --dir download/TritonDFT-43C7 \
  --max-conns 4
```

## How it works

The script performs the following steps:

1. extract the repository name from the anonymous.4open.science URL
2. recursively list files using the current API endpoint:
   - repository root: `/api/repo/<repo>/files/`
   - subdirectories: `/api/repo/<repo>/files/?path=<subdir>`
3. build file download URLs with `/api/repo/<repo>/file/<path>`
4. download files concurrently with retries and backoff
5. skip already-complete files and verify output sizes

## Notes on reliability

The anonymous.4open.science service may occasionally return:

- SSL EOF / connection reset style failures
- `429 Too Many Requests`
- partial transfers on large repositories

This fork adds retry logic and conservative concurrency to make these cases more manageable, but repeated retries may still be needed for very large repositories.

## Limitations

- this script is not a full `git clone`; it downloads the file contents exposed by anonymous.4open.science
- submodule behavior depends on what the anonymous mirror exposes
- service-side API changes may require future updates

## Acknowledgement

Thanks to [tdurieux's Anonymous Github project](https://github.com/tdurieux/anonymous_github)
and [ShoufaChen's Anonymous Github project](https://github.com/ShoufaChen/clone-anonymous4open)
