"""Start or check a BESTIARY render from Codex Cloud."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path, payload=None):
    request = urllib.request.Request(
        API + path, data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + os.environ["BESTIARY_GITHUB_TOKEN"],
                 "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2026-03-10"})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
        return json.load(response)


def links(base, run):
    tag = f"bestiary-{run['run_number']}-{run['run_attempt']}"
    try:
        release = api(f"{base}/releases/tags/{tag}")
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise
        return {}
    return {item["name"]: item["browser_download_url"] for item in release["assets"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--topic")
    group.add_argument("--status", type=int, metavar="RUN_ID")
    parser.add_argument("--episode")
    parser.add_argument("--mode", choices=["produce", "plan", "recorded"], default="produce")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS")
    args = parser.parse_args()
    repo = os.getenv("BESTIARY_REPO", "")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repo):
        raise ValueError("Set BESTIARY_REPO = OWNER/REPO di environment Codex Cloud.")
    if not os.getenv("BESTIARY_GITHUB_TOKEN"):
        raise ValueError("Tambahkan HTTP secret BESTIARY_GITHUB_TOKEN di Codex Cloud.")
    if not 0 <= args.wait <= 1500:
        raise ValueError("--wait harus 0–1500 detik.")
    base = f"/repos/{repo}"
    if args.status is not None:
        if args.status < 1:
            raise ValueError("Run ID harus angka positif.")
        run_id = args.status
    else:
        topic = args.topic.strip()
        if not 1 <= len(topic) <= 120 or any(ord(ch) < 32 for ch in topic):
            raise ValueError("Isi nama spesies sepanjang 1–120 karakter.")
        if args.episode and not re.fullmatch(r"EP[0-9]{2,4}", args.episode):
            raise ValueError("Gunakan format nomor seperti EP16.")
        repository = api(base)
        if repository["visibility"] != "private":
            raise ValueError("Pilih repo BESTIARY Private.")
        response = api(base + "/actions/workflows/produce.yml/dispatches", {
            "ref": repository["default_branch"],
            "inputs": {"topic": topic, "episode": args.episode or "", "mode": args.mode},
        })
        run_id = response["workflow_run_id"]
        print(json.dumps({"run_id": run_id, "run_url": response["html_url"], "status": "submitted"}), flush=True)
        if not args.wait:
            return
    deadline = time.monotonic() + args.wait
    while True:
        try:
            run = api(f"{base}/actions/runs/{run_id}")
        except urllib.error.HTTPError as err:
            if err.code != 404 or time.monotonic() >= deadline:
                raise
        else:
            if run["status"] == "completed" or time.monotonic() >= deadline:
                print(json.dumps({
                    "run_id": run_id, "run_url": run["html_url"], "status": run["status"],
                    "conclusion": run["conclusion"],
                    "files": links(base, run) if run["status"] == "completed" else {},
                }, ensure_ascii=False), flush=True)
                return
        time.sleep(min(15, max(0, deadline-time.monotonic())))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as err:
        sys.exit(f"GitHub HTTP {err.code}. Periksa izin token, repo, workflow, dan Run ID sebelum mencoba lagi.")
    except (OSError, ValueError, KeyError) as err:
        sys.exit(f"BESTIARY: {err}")
