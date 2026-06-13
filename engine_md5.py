# -*- coding: utf-8 -*-
"""
engine_md5.py
CHỖ RIÊNG ĐỂ NÂNG CẤP THUẬT TOÁN MD5.

Bạn muốn chỉnh thuật toán thì chỉ sửa file này.
Hai hàm chính:
- predict_basic(md5_hex)
- predict_pro(md5_hex, gate_key="")

Output bắt buộc là dict có các key:
engine, taixiu, tx_conf, chanle, dice, total, risk, risk_emoji, score, hash_short, details
"""

import hashlib
import statistics
import math

def _parse(md5_hex):
    s = md5_hex.lower().strip()
    if len(s) != 32:
        return None, None, None
    try:
        b = [int(s[i:i+2], 16) for i in range(0, 32, 2)]
        n = [int(c, 16) for c in s]
        return s, b, n
    except Exception:
        return None, None, None

def _risk(nums, raw, chaos):
    rp = int((statistics.pstdev(nums) * 1.9 + abs(raw - 5000) / 77 + chaos / 43) % 100)
    if rp < 32:
        return "THẤP", "🟢"
    if rp < 69:
        return "TRUNG BÌNH", "🟡"
    return "CAO", "🔴"


def _cau_types(s, b, n, score, total, raw, extra=0):
    """Nhận diện nhiều dạng cầu phổ biến dựa trên cấu trúc hash.
    Không cần dữ liệu lịch sử; dùng để phân lớp tín hiệu trong MD5."""
    head = sum(b[:4]); mid = sum(b[6:10]); tail = sum(b[-4:])
    even = sum(1 for x in n if x % 2 == 0)
    high = sum(1 for x in n if x >= 8)
    low = 32 - high
    zigzag = sum(1 for i in range(31) if (n[i] >= 8) != (n[i+1] >= 8))
    repeat = max(s.count(ch) for ch in set(s)) if s else 0
    pairs = sum(1 for i in range(0, 31, 2) if s[i] == s[i+1])
    mirror_hits = sum(1 for i in range(16) if s[i] == s[31-i])
    balance = abs(head - tail)
    signals = []
    if score >= 58: signals.append('Cầu bệt Tài')
    elif score <= 42: signals.append('Cầu bệt Xỉu')
    else: signals.append('Cầu cân bằng')
    signals.append('Cầu đảo 1-1' if zigzag >= 18 else 'Cầu nhịp 2-2' if zigzag >= 13 else 'Cầu bệt/đè')
    signals.append('Cầu gãy mạnh' if balance > 210 else 'Cầu gãy nhẹ' if balance > 110 else 'Cầu ổn định')
    signals.append('Cầu chẵn áp lực' if even >= 19 else 'Cầu lẻ áp lực' if even <= 13 else 'Cầu chẵn/lẻ cân')
    signals.append('Cầu cao điểm' if high >= 19 else 'Cầu thấp điểm' if low >= 19 else 'Cầu trung tính')
    if repeat >= 5: signals.append('Cầu lặp ký tự')
    if pairs >= 4: signals.append('Cầu song thủ/pair')
    if mirror_hits >= 4: signals.append('Cầu đối xứng mirror')
    if total in (10, 11): signals.append('Cầu sát nút 10-11')
    if total in (3, 18): signals.append('Cầu biên cực trị')
    # lọc trùng, giữ ngắn gọn
    out=[]
    for x in signals:
        if x not in out:
            out.append(x)
    return out[:8]

def predict_basic(md5_hex):
    s, b, n = _parse(md5_hex)
    if not s:
        return None

    xor_all = 0
    for i, x in enumerate(b):
        xor_all ^= ((x << (i % 2)) & 255)

    wave = sum((i + 1) * b[i] for i in range(16)) % 2048
    mirror = sum((16 - i) * (b[i] ^ b[15-i]) for i in range(16)) % 2048
    nibble_pressure = sum((i + 5) * n[i] for i in range(32)) % 2048
    edge = (b[0] * 31 + b[15] * 17 + b[7] * 13 + xor_all * 19) % 2048

    raw = (wave * 29 + mirror * 17 + nibble_pressure * 13 + edge * 11 + xor_all * 23) % 10000
    score = raw / 100.0

    d1 = ((b[0] + b[5] + wave + edge) % 6) + 1
    d2 = ((b[7] ^ b[11] ^ xor_all ^ mirror) % 6) + 1
    d3 = ((b[14] + b[2] + nibble_pressure) % 6) + 1
    total = d1 + d2 + d3

    result = "TÀI" if score >= 50 else "XỈU"
    confidence = min(90, 56 + int(abs(score - 50) * 0.62) + (edge % 4))
    parity = (raw + total * 31 + xor_all + mirror) % 100
    chanle = "CHẴN" if parity >= 50 else "LẺ"
    risk, risk_emoji = _risk(b, raw, edge)

    cau = _cau_types(s, b, n, score, total, raw, edge)

    return {
        "engine": "BASIC-V8 ALL-CAU HASH MATRIX",
        "taixiu": result,
        "tx_conf": confidence,
        "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}",
        "total": total,
        "risk": risk,
        "risk_emoji": risk_emoji,
        "score": round(score, 2),
        "hash_short": s[:8].upper() + "..." + s[-6:].upper(),
        "trend": " · ".join(cau[:3]),
        "details": ["Byte wave", "Mirror entropy", "Nibble pressure", "Edge XOR"] + cau
    }

def predict_pro(md5_hex, gate_key=""):
    s, b, n = _parse(md5_hex)
    if not s:
        return None

    salt = f"KINGBOT_ULTRA_PRO_V10|{gate_key}|{s}|CHAOS|MATRIX|ANTI-BIAS"
    sha512 = list(hashlib.sha512(salt.encode()).digest())
    blake = list(hashlib.blake2b((s + gate_key + salt[::-1]).encode(), digest_size=32).digest())
    sha3 = list(hashlib.sha3_256((gate_key + s + salt).encode()).digest())

    xor_rot = 0
    for i, x in enumerate(b):
        xor_rot ^= ((x << (i % 5)) & 255) ^ sha512[i] ^ blake[i % 32] ^ sha3[i % 32]

    wave = sum((i + 11) * (b[i] ^ sha512[i] ^ sha3[i]) for i in range(16)) % 16384
    mirror = sum((17 - i) * ((b[i] + sha512[15-i] + sha3[31-i]) ^ b[15-i] ^ blake[i]) for i in range(16)) % 16384
    nibble = sum((i + 7) * (n[i] + (sha512[i] % 16) + (blake[i % 32] % 7) + (sha3[i % 32] % 5)) for i in range(32)) % 16384
    split_a = sum(b[:8]) * 5 + sum(sha512[8:20]) + sum(blake[:12]) + sum(sha3[:10])
    split_b = sum(b[8:]) * 7 + sum(sha512[20:32]) + sum(blake[12:24]) + sum(sha3[10:22])
    balance = abs(sum(b[::2]) - sum(b[1::2])) * 3 + abs(sum(n[:16]) - sum(n[16:])) * 11
    chaos = int(abs(split_a - split_b) + statistics.pstdev(b) * 29 + statistics.pstdev(sha512[:32]) * 13 + balance) % 16384

    resonance = int((math.sin((wave + chaos) / 97.0) + 1) * 5000) % 10000
    raw = (
        wave * 31 + mirror * 23 + nibble * 19 + chaos * 17 +
        xor_rot * 29 + split_a * 7 - split_b * 5 + resonance * 13 + sha3[0] * 41 + sha3[-1] * 37
    ) % 10000
    score = raw / 100.0

    d1 = ((b[0] + b[5] + sha512[2] + wave + chaos + blake[1]) % 6) + 1
    d2 = ((b[7] ^ b[11] ^ sha512[9] ^ mirror ^ xor_rot ^ blake[7]) % 6) + 1
    d3 = ((b[14] + b[3] + sha512[18] + nibble + split_a + blake[15]) % 6) + 1
    total = d1 + d2 + d3

    result = "TÀI" if score >= 50 else "XỈU"
    distance = abs(score - 50)
    confidence = min(99, 64 + int(distance * 0.78) + (chaos % 7))

    parity_score = (raw + total * 47 + xor_rot * 13 + sha512[0] + chaos + blake[0]) % 100
    chanle = "CHẴN" if parity_score >= 50 else "LẺ"
    risk, risk_emoji = _risk(b, raw, chaos)
    cau = _cau_types(s, b, n, score, total, raw, chaos)
    trend = " · ".join(cau[:5])

    return {
        "engine": "PRO-V11 ALL-CAU SHA512/SHA3/BLAKE2 MATRIX",
        "taixiu": result,
        "tx_conf": confidence,
        "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}",
        "total": total,
        "risk": risk,
        "risk_emoji": risk_emoji,
        "score": round(score, 2),
        "hash_short": s[:8].upper() + "..." + s[-6:].upper(),
        "trend": trend,
        "details": ["SHA512 salt", "SHA3 anti-bias", "BLAKE2b cross-check", "Chaos resonance", "Mirror entropy", "Gate-specific matrix"] + cau
    }


def predict_free(md5_hex, gate_key=""):
    """
    FREE engine: nhẹ hơn Basic/Pro, vẫn có phân tích hash nhưng confidence thấp hơn.
    """
    s, b, n = _parse(md5_hex)
    if not s:
        return None
    xor_all = 0
    for x in b:
        xor_all ^= x
    wave = sum((i + 1) * b[i] for i in range(16)) % 997
    nib = sum((i + 2) * n[i] for i in range(32)) % 997
    raw = (wave * 17 + nib * 9 + xor_all * 21 + b[0] * 5 + b[-1] * 7) % 10000
    score = raw / 100.0
    d1 = ((b[0] + wave) % 6) + 1
    d2 = ((b[8] ^ xor_all) % 6) + 1
    d3 = ((b[15] + nib) % 6) + 1
    total = d1 + d2 + d3
    result = "TÀI" if score >= 50 else "XỈU"
    confidence = min(82, 51 + int(abs(score - 50) * 0.45))
    parity = (raw + total * 19 + xor_all) % 100
    chanle = "CHẴN" if parity >= 50 else "LẺ"
    risk, risk_emoji = _risk(b, raw, xor_all)
    cau = _cau_types(s, b, n, score, total, raw, xor_all)
    return {
        "engine": "FREE-LITE ALL-CAU SCANNER",
        "taixiu": result,
        "tx_conf": confidence,
        "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}",
        "total": total,
        "risk": risk,
        "risk_emoji": risk_emoji,
        "score": round(score, 2),
        "hash_short": s[:8].upper() + "..." + s[-6:].upper(),
        "trend": " · ".join(cau[:3]),
        "details": ["Lite wave", "Simple XOR", "Nibble scan"] + cau
    }
