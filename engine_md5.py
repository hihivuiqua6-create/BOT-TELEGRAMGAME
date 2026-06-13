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

    return {
        "engine": "BASIC-V7 QUANTUM HASH MATRIX",
        "taixiu": result,
        "tx_conf": confidence,
        "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}",
        "total": total,
        "risk": risk,
        "risk_emoji": risk_emoji,
        "score": round(score, 2),
        "hash_short": s[:8].upper() + "..." + s[-6:].upper(),
        "details": ["Byte wave", "Mirror entropy", "Nibble pressure", "Edge XOR"]
    }

def predict_pro(md5_hex, gate_key=""):
    s, b, n = _parse(md5_hex)
    if not s:
        return None

    salt = f"KINGBOT_ULTRA_PRO_V9|{gate_key}|{s}|CHAOS|MATRIX"
    sha512 = list(hashlib.sha512(salt.encode()).digest())
    blake = list(hashlib.blake2b((s + gate_key).encode(), digest_size=32).digest())

    xor_rot = 0
    for i, x in enumerate(b):
        xor_rot ^= ((x << (i % 5)) & 255) ^ sha512[i] ^ blake[i % 32]

    wave = sum((i + 11) * (b[i] ^ sha512[i]) for i in range(16)) % 8192
    mirror = sum((17 - i) * ((b[i] + sha512[15-i]) ^ b[15-i] ^ blake[i]) for i in range(16)) % 8192
    nibble = sum((i + 7) * (n[i] + (sha512[i] % 16) + (blake[i % 32] % 7)) for i in range(32)) % 8192
    split_a = sum(b[:8]) * 5 + sum(sha512[8:20]) + sum(blake[:12])
    split_b = sum(b[8:]) * 7 + sum(sha512[20:32]) + sum(blake[12:24])
    chaos = int(abs(split_a - split_b) + statistics.pstdev(b) * 23 + statistics.pstdev(sha512[:32]) * 11) % 8192

    resonance = int((math.sin((wave + chaos) / 97.0) + 1) * 5000) % 10000
    raw = (
        wave * 31 + mirror * 23 + nibble * 19 + chaos * 17 +
        xor_rot * 29 + split_a * 7 - split_b * 5 + resonance * 13
    ) % 10000
    score = raw / 100.0

    d1 = ((b[0] + b[5] + sha512[2] + wave + chaos + blake[1]) % 6) + 1
    d2 = ((b[7] ^ b[11] ^ sha512[9] ^ mirror ^ xor_rot ^ blake[7]) % 6) + 1
    d3 = ((b[14] + b[3] + sha512[18] + nibble + split_a + blake[15]) % 6) + 1
    total = d1 + d2 + d3

    result = "TÀI" if score >= 50 else "XỈU"
    distance = abs(score - 50)
    confidence = min(98, 63 + int(distance * 0.76) + (chaos % 6))

    parity_score = (raw + total * 47 + xor_rot * 13 + sha512[0] + chaos + blake[0]) % 100
    chanle = "CHẴN" if parity_score >= 50 else "LẺ"
    risk, risk_emoji = _risk(b, raw, chaos)
    trend = "Cầu nghiêng Tài" if score >= 57 else ("Cầu nghiêng Xỉu" if score <= 43 else "Cầu cân bằng")

    return {
        "engine": "PRO-V9 SHA512/BLAKE2 CHAOS MATRIX",
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
        "details": ["SHA512 salt", "BLAKE2b cross-check", "Chaos resonance", "Mirror entropy", "Gate-specific matrix"]
    }
