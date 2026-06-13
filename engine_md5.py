# -*- coding: utf-8 -*-
"""
engine_md5.py
Engine dự đoán MD5 nâng cấp: multi-hash, multi-cầu, chống lệch bias.
Lưu ý: MD5 là hash một chiều nên không có thuật toán nào đảm bảo đúng 100%; engine này chỉ phân tích tham khảo.
"""
import hashlib, statistics, math

HEX = set('0123456789abcdefABCDEF')

def _parse(md5_hex):
    s = str(md5_hex or '').lower().strip()
    if len(s) != 32 or any(c not in HEX for c in s):
        return None, None, None
    b = [int(s[i:i+2], 16) for i in range(0, 32, 2)]
    n = [int(c, 16) for c in s]
    return s, b, n

def _risk(nums, raw, chaos):
    rp = int((statistics.pstdev(nums) * 2.7 + abs(raw - 5000) / 61 + chaos / 37) % 100)
    if rp < 28: return 'THẤP', '🟢'
    if rp < 66: return 'TRUNG BÌNH', '🟡'
    return 'CAO', '🔴'

def _digest_bytes(*parts, algo='sha512', size=64):
    data = '|'.join(str(x) for x in parts).encode('utf-8', 'ignore')
    if algo == 'sha512': return list(hashlib.sha512(data).digest())
    if algo == 'sha3': return list(hashlib.sha3_512(data).digest())
    if algo == 'blake': return list(hashlib.blake2b(data, digest_size=size).digest())
    return list(hashlib.sha256(data).digest())

def _streak_features(n):
    inc = dec = same = alt = 0
    for i in range(1, len(n)):
        if n[i] > n[i-1]: inc += 1
        if n[i] < n[i-1]: dec += 1
        if n[i] == n[i-1]: same += 1
        if (n[i] % 2) != (n[i-1] % 2): alt += 1
    head_tail = sum(n[:8]) - sum(n[-8:])
    odd_even = sum(x % 2 for x in n) - (len(n) - sum(x % 2 for x in n))
    return inc, dec, same, alt, head_tail, odd_even

def _core(md5_hex, gate_key='', level='basic'):
    s, b, n = _parse(md5_hex)
    if not s: return None
    salt = f'KINGBOT-MD5-OMNI-CAU-V18|{level}|{gate_key}|{s}|TAI-XIU|ANTI-BIAS'
    sha = _digest_bytes(salt, s, algo='sha512')
    sha3 = _digest_bytes(gate_key, s, salt[::-1], algo='sha3')
    blake = _digest_bytes(s, salt, gate_key, algo='blake', size=64)
    h2 = _digest_bytes(s[::-1], gate_key, level, algo='sha256')

    xor_rot = 0
    for i, x in enumerate(b):
        xor_rot ^= ((x << (i % 7)) & 255) ^ sha[i] ^ sha3[63-i] ^ blake[(i*3) % 64]
    inc, dec, same, alt, head_tail, odd_even = _streak_features(n)

    # Các lớp cầu: bệt, đảo, 1-1, 2-1, đối xứng, đầu/đuôi, chẵn/lẻ, byte wave, nibble wave.
    cau_bet = (same * 97 + abs(head_tail) * 13 + sha[1] * 7 + b[0] * 11) % 10000
    cau_dao = (alt * 173 + abs(odd_even) * 59 + sha3[2] * 17 + b[-1] * 19) % 10000
    cau_21 = (sum((i % 3 + 1) * n[i] for i in range(32)) * 29 + blake[3] * 31) % 10000
    cau_mirror = sum((17-i) * ((b[i] ^ b[15-i]) + sha[i] + blake[15-i]) for i in range(16)) % 10000
    cau_wave = sum((i+5) * (b[i] + sha[i] + sha3[i]) for i in range(16)) % 10000
    cau_tail = (int(s[-8:], 16) + int(s[:8], 16) + sum(h2) * 23) % 10000
    entropy = int((statistics.pstdev(b) * 181 + statistics.pvariance(n) * 97 + abs(sum(b[:8])-sum(b[8:])) * 11)) % 10000
    resonance = int((math.sin((cau_wave + entropy + xor_rot) / 101.0) + 1) * 5000) % 10000

    raw = (cau_bet*11 + cau_dao*13 + cau_21*17 + cau_mirror*19 + cau_wave*23 + cau_tail*29 + entropy*31 + resonance*37 + xor_rot*41) % 10000
    score = raw / 100.0

    # Hội đồng vote để tránh 1 công thức bị lệch.
    votes = []
    layers = [cau_bet, cau_dao, cau_21, cau_mirror, cau_wave, cau_tail, entropy, resonance, raw]
    for i, val in enumerate(layers):
        votes.append(1 if ((val + sha[i] + blake[i*2] + sha3[i*3]) % 100) >= 50 else -1)
    vote_sum = sum(votes)
    result = 'TÀI' if (score >= 50 and vote_sum >= -1) or vote_sum >= 3 else 'XỈU'

    d1 = ((b[0] + b[5] + sha[7] + cau_wave + xor_rot) % 6) + 1
    d2 = ((b[7] ^ b[11] ^ sha3[9] ^ cau_mirror ^ blake[8]) % 6) + 1
    d3 = ((b[14] + b[3] + blake[17] + cau_tail + entropy) % 6) + 1
    total = d1 + d2 + d3
    if result == 'TÀI' and total < 11:
        d3 = min(6, d3 + (11-total)); total = d1+d2+d3
    if result == 'XỈU' and total > 10:
        d3 = max(1, d3 - (total-10)); total = d1+d2+d3

    distance = abs(score - 50)
    agreement = abs(vote_sum) / len(votes)
    base = 55 if level == 'free' else (62 if level == 'basic' else 68)
    cap = 84 if level == 'free' else (92 if level == 'basic' else 99)
    confidence = min(cap, base + int(distance * (0.42 if level=='free' else 0.62)) + int(agreement * 18) + (entropy % 5))
    parity_score = (raw + total*47 + xor_rot*13 + sha[0] + sha3[1] + blake[2]) % 100
    chanle = 'CHẴN' if parity_score >= 50 else 'LẺ'
    risk, risk_emoji = _risk(b, raw, entropy + xor_rot)
    if vote_sum >= 4: trend = 'Cầu tổng hợp nghiêng Tài'
    elif vote_sum <= -4: trend = 'Cầu tổng hợp nghiêng Xỉu'
    elif score >= 57: trend = 'Cầu điểm nghiêng Tài'
    elif score <= 43: trend = 'Cầu điểm nghiêng Xỉu'
    else: trend = 'Cầu cân bằng / nên đi vốn nhỏ'
    return {
        'engine': {'free':'FREE-OMNI CAU V18','basic':'BASIC-OMNI CAU V18','pro':'PRO-OMNI SHA512/SHA3/BLAKE V18'}.get(level, 'OMNI CAU V18'),
        'taixiu': result, 'tx_conf': int(confidence), 'chanle': chanle,
        'dice': f'{d1}-{d2}-{d3}', 'total': total,
        'risk': risk, 'risk_emoji': risk_emoji, 'score': round(score, 2),
        'hash_short': s[:8].upper() + '...' + s[-6:].upper(),
        'trend': trend,
        'details': ['Cầu bệt', 'Cầu đảo', 'Cầu 2-1/1-2', 'Cầu mirror', 'Byte wave', 'Nibble entropy', 'Multi-hash vote', 'Gate salt']
    }

def predict_free(md5_hex, gate_key=''):
    return _core(md5_hex, gate_key, 'free')

def predict_basic(md5_hex):
    return _core(md5_hex, '', 'basic')

def predict_pro(md5_hex, gate_key=''):
    return _core(md5_hex, gate_key, 'pro')
