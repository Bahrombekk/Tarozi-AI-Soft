#!/usr/bin/env python3
"""
====================================================
  TAROZI CLIENT - Kompyuter  v3.0
  Muallif: Bahrombek
  Ishlatish: python3 client.py
====================================================

O'rnatish (bir marta):
  pip install requests
"""

import requests
import socket
import time
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════════════════════════════════
#  SOZLAMALAR
# ══════════════════════════════════════════
PI_HOST  = None          # None = avtomatik topadi
                         # yoki '192.168.136.90' / 'bahrombek-pi.local'
PORT     = 8000
LOGIN    = "bahrombek"
PAROL    = "123"
INTERVAL = 1.0
# ══════════════════════════════════════════

BASE_URL = ""
AUTH     = (LOGIN, PAROL)


# ══════════════════════════════════════════
#  AVTOMATIK SERVER TOPISH
# ══════════════════════════════════════════
def auto_find_server() -> str | None:
    """
    Tarmoqdagi barcha IP larni parallel skanerlaydi.
    /massa endpoint ga so'rov yuborib, javob bergan Pi ni topadi.

    Returns:
        IP manzil yoki None
    """
    # 1. Avval hostname bilan sinab ko'r (Bonjour/mDNS)
    for hostname in ["bahrombek-pi.local", "raspberrypi.local"]:
        try:
            ip = socket.gethostbyname(hostname)
            if _ping_server(ip):
                print(f"  [AUTO] mDNS orqali topildi: {hostname} → {ip}")
                return ip
        except:
            pass

    # 2. Tarmoq subnetini aniqlash
    subnet = _get_subnet()
    if not subnet:
        return None

    print(f"  [AUTO] Tarmoq skanerlanmoqda: {subnet}.0/24")
    print(f"  [AUTO] Bu 10-20 soniya olishi mumkin...")

    # 3. Barcha IP larni parallel tekshirish (254 ta)
    ips = [f"{subnet}.{i}" for i in range(1, 255)]

    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(_ping_server, ip): ip for ip in ips}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                if future.result():
                    print(f"  [AUTO] Server topildi: {ip}")
                    return ip
            except:
                pass

    return None


def _ping_server(ip: str) -> bool:
    """IP ga /massa so'rov yuborib, tarozi serveri ekanini tekshiradi"""
    try:
        resp = requests.get(
            f"http://{ip}:{PORT}/",
            timeout=0.8,
        )
        if resp.status_code == 200:
            data = resp.json()
            # "Tarozi Server" tekshirish
            return "server" in data and "Tarozi" in str(data.get("server", ""))
    except:
        pass
    return False


def _get_subnet() -> str | None:
    """Kompyuterning lokal IP subnetini aniqlaydi (masalan: 192.168.136)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        parts = local_ip.split(".")
        return ".".join(parts[:3])
    except:
        return None


# ══════════════════════════════════════════
#  EKRAN
# ══════════════════════════════════════════
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def draw_bar(value, min_val=500, max_val=50000, width=38):
    ratio  = max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    filled = int(ratio * width)
    return f"[{'█' * filled}{'░' * (width - filled)}] {ratio*100:.1f}%"


def print_screen(data, net_errors):
    massa      = data["massa"]
    unit       = data["unit"]
    updated    = data.get("updated", "--")
    readings   = data.get("readings", 0)
    sensor_ok  = data.get("sensor_ok", True)
    sensor_err = data.get("sensor_error", "")
    port       = data.get("port") or "--"
    now        = datetime.now().strftime("%H:%M:%S")

    clear()
    print("╔══════════════════════════════════════════════╗")
    print("║        TAROZI MONITORING TIZIMI  v3.0        ║")
    print(f"║  Server : {PI_HOST:<35}║")
    print(f"║  Port   : {port:<35}║")
    print("╠══════════════════════════════════════════════╣")

    if not sensor_ok:
        print("║                                              ║")
        print("║   !!!  SENSOR XATOSI                         ║")
        print("║                                              ║")
        for line in sensor_err.split('\n'):
            for chunk in [line[i:i+43] for i in range(0, max(1, len(line)), 43)]:
                print(f"║  {chunk:<44}║")
        print("║                                              ║")
        print("╠══════════════════════════════════════════════╣")
        print(f"║  Oxirgi massa : {massa:>10.1f} kg                  ║")
        print(f"║  Oxirgi vaqt  : {updated:<28}║")
    else:
        print(f"║                                              ║")
        print(f"║   MASSA:  {massa:>10.1f} {unit:<30}║")
        print(f"║                                              ║")
        print(f"║  {draw_bar(massa):<44}║")
        print(f"║                                              ║")
        print("╠══════════════════════════════════════════════╣")

    print("╠══════════════════════════════════════════════╣")
    print(f"║  So'rovlar : {readings:<5}  |  Vaqt : {now}         ║")

    if net_errors > 0:
        print(f"║  !!! Tarmoq xatolari: {net_errors:<23}║")
    else:
        print(f"║  Tarmoq: OK{'':<34}║")

    print("╚══════════════════════════════════════════════╝")
    print("\n  [Ctrl+C] - chiqish")


# ══════════════════════════════════════════
#  ASOSIY LOOP
# ══════════════════════════════════════════
def run():
    net_errors = 0

    while True:
        try:
            resp = requests.get(f"{BASE_URL}/massa", auth=AUTH, timeout=3)

            if resp.status_code == 200:
                net_errors = 0
                print_screen(resp.json(), net_errors)

            elif resp.status_code == 401:
                clear()
                print("\n  [XATO] Login yoki parol noto'g'ri!")
                print(f"  LOGIN = '{LOGIN}'")
                print(f"  PAROL = '{PAROL}'")
                print("\n  client.py ichida LOGIN va PAROL ni to'g'rilang.")
                sys.exit(1)

            else:
                clear()
                print(f"\n  [XATO] Server javobi: {resp.status_code}")

        except requests.ConnectionError:
            net_errors += 1
            clear()
            print(f"\n  [XATO] Serverga ulanib bo'lmadi!")
            print(f"  Manzil          : {PI_HOST}:{PORT}")
            print(f"  Urinishlar soni : {net_errors}")
            print("\n  Tekshiring:")
            print("   1. Pi yoqilganmi?")
            print("   2. Bir tarmoqdamisiz?")
            print(f"   3. ping {PI_HOST}")
            print("\n  Qayta urinilmoqda...")
            time.sleep(4)

        except requests.Timeout:
            net_errors += 1
            clear()
            print(f"\n  [XATO] Server javob bermadi (timeout 3s)")
            print(f"  Urinishlar soni: {net_errors}")

        except KeyboardInterrupt:
            print("\n\n  Dastur to'xtatildi.")
            sys.exit(0)

        time.sleep(INTERVAL)


# ══════════════════════════════════════════
#  ISHGA TUSHIRISH
# ══════════════════════════════════════════
def main():
    global PI_HOST, BASE_URL

    print("=" * 50)
    print("   TAROZI CLIENT v3.0")
    print("=" * 50)

    # 1. Qo'lda belgilangan bo'lsa — shuni ishlat
    if PI_HOST:
        print(f"\n  Server: {PI_HOST}:{PORT}")
        BASE_URL = f"http://{PI_HOST}:{PORT}"
        try:
            resp = requests.get(f"{BASE_URL}/", timeout=3)
            if resp.status_code == 200:
                print("  [OK] Server topildi!")
            else:
                print(f"  [XATO] Status: {resp.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"  [XATO] Ulanib bo'lmadi: {e}")
            sys.exit(1)

    # 2. Avtomatik qidirish
    else:
        print("\n  PI_HOST = None — tarmoq skanerlanmoqda...")
        found = auto_find_server()

        if found:
            PI_HOST  = found
            BASE_URL = f"http://{PI_HOST}:{PORT}"
            print(f"  [OK] Server topildi: {PI_HOST}")
        else:
            print("\n  [XATO] Tarmoqda tarozi serveri topilmadi!")
            print("\n  Tekshiring:")
            print("   1. Pi yoqilganmi?")
            print("   2. pi_server.py ishlamoqdami?")
            print("   3. Bir tarmoqdamisiz?")
            print("\n  Yoki client.py da PI_HOST ni qo'lda kiriting:")
            ip = input("  IP manzil: ").strip()
            if ip:
                PI_HOST  = ip
                BASE_URL = f"http://{PI_HOST}:{PORT}"
            else:
                sys.exit(1)

    print(f"\n  Monitoring boshlanyapti → {BASE_URL}")
    time.sleep(1)
    run()


if __name__ == "__main__":
    main()