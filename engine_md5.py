# -*- coding: utf-8 -*-
"""
KINGBOT MD5/HITCLUB HASH ENGINE V30
- Nhận hash hex 32 ký tự (MD5) hoặc 64 ký tự (SHA256/HitClub mẫu).
- 3 cấp thuật toán: free < basic < pro về số lớp phân tích và confidence cap.
- Lưu ý thật: hash là dữ liệu một chiều, không thuật toán nào đảm bảo đúng 100%; engine chỉ phân tích tham khảo.
"""
import hashlib, statistics, math

HEX = set("0123456789abcdefABCDEF")

def _parse(hash_hex):
    s = str(hash_hex or "").lower().strip().replace(" ", "")
    if len(s) not in (32, 64) or any(c not in HEX for c in s):
        return None, None, None, None
    b = [int(s[i:i+2], 16) for i in range(0, len(s), 2)]
    n = [int(c, 16) for c in s]
    kind = "MD5" if len(s) == 32 else "HITCLUB/SHA256"
    return s, b, n, kind

def _digest(tag, *parts, size=64):
    data = (tag + "|" + "|".join(map(str, parts))).encode("utf-8", "ignore")
    a = list(hashlib.sha512(data).digest())
    b = list(hashlib.sha3_512(data[::-1]).digest())
    c = list(hashlib.blake2b(data + bytes(a[:16]), digest_size=size).digest())
    d = list(hashlib.sha256(data + bytes(b[:16])).digest())
    return (a + b + c + d)

def _streak(n):
    inc=dec=same=alt=zig=0
    for i in range(1, len(n)):
        inc += n[i] > n[i-1]
        dec += n[i] < n[i-1]
        same += n[i] == n[i-1]
        alt += (n[i] & 1) != (n[i-1] & 1)
        if i > 1:
            zig += (n[i]-n[i-1]) * (n[i-1]-n[i-2]) < 0
    return inc, dec, same, alt, zig

def _risk(vals, raw, entropy):
    rp = int((statistics.pstdev(vals) * 2.4 + abs(raw - 5000) / 64 + entropy / 41) % 100)
    if rp < 30: return "THẤP", "🟢"
    if rp < 67: return "TRUNG BÌNH", "🟡"
    return "CAO", "🔴"

def _core(hash_hex, gate_key="", level="basic"):
    s, b, n, kind = _parse(hash_hex)
    if not s: return None
    L = len(b)
    tag = f"KINGBOT-V30-OMNI-CAU|{kind}|{level}|{gate_key}|{s}"
    h = _digest(tag, s, s[::-1], gate_key, level, size=64)

    inc, dec, same, alt, zig = _streak(n)
    front = sum(b[:L//2]); back = sum(b[L//2:]); even = sum(b[::2]); odd = sum(b[1::2])
    nib_front = sum(n[:len(n)//2]); nib_back = sum(n[len(n)//2:])
    xor = 0
    for i, x in enumerate(b):
        xor ^= ((x << (i % 7)) & 255) ^ h[i] ^ h[(255-i) % len(h)]
    rot = sum(((b[i] << (i % 5)) & 255) ^ h[(i*11) % len(h)] for i in range(L)) % 10000

    # Bộ nhận diện cầu: bệt, đảo, 1-1, 2-1, 3-1, sandwich, mirror, đầu/đuôi, chẵn/lẻ, entropy, byte-wave, nibble-wave.
    layers = []
    layers.append((same*211 + abs(front-back)*17 + h[1]*13 + b[0]*19) % 10000)                 # cầu bệt
    layers.append((alt*197 + zig*149 + abs(even-odd)*23 + h[2]*29 + b[-1]*31) % 10000)       # cầu đảo
    layers.append((sum((i%2+1)*n[i] for i in range(len(n))) * 37 + h[3]*41) % 10000)          # 1-1
    layers.append((sum((i%3+1)*n[i] for i in range(len(n))) * 43 + h[4]*47) % 10000)          # 2-1 / 1-2
    layers.append((sum((i%4+1)*n[i] for i in range(len(n))) * 53 + h[5]*59) % 10000)          # 3-1
    layers.append((sum((i+7)*((b[i] ^ b[L-1-i]) + h[(i*3)%len(h)]) for i in range(L)) ) % 10000) # mirror
    layers.append((int(s[:8],16) + int(s[-8:],16) + front*17 + back*19 + h[6]*61) % 10000)   # đầu đuôi
    layers.append((nib_front*83 - nib_back*71 + alt*67 + h[7]*73) % 10000)                    # nibble áp lực
    layers.append((sum((i+5)*(b[i] + h[i] + h[(i*5)%len(h)]) for i in range(L))) % 10000)     # byte wave
    layers.append(int((statistics.pstdev(b)*181 + statistics.pvariance(n)*97 + abs(front-back)*13 + abs(even-odd)*11)) % 10000) # entropy
    layers.append(int((math.sin((sum(layers)+xor+rot)/113.0)+1)*5000) % 10000)                # resonance
    layers.append((sum(layers)*7 + xor*101 + rot*103 + sum(h[:64])*3) % 10000)                # final pressure

    # Free dùng ít lớp hơn và confidence thấp hơn; Basic dùng nhiều lớp hơn; Pro dùng full hội đồng.
    if level == "free": used = layers[:5] + [layers[9]]
    elif level == "basic": used = layers[:9] + [layers[10]]
    else: used = layers

    weights = [11,13,17,19,23,29,31,37,41,43,47,53]
    raw = sum(v * weights[i % len(weights)] for i, v in enumerate(used)) % 10000
    score = raw / 100.0
    votes = []
    for i, v in enumerate(used):
        gate_bias = h[(i*17+5) % len(h)] + h[(i*31+9) % len(h)] + (0 if level == "free" else xor)
        votes.append(1 if ((v + gate_bias + raw) % 100) >= 50 else -1)
    vote_sum = sum(votes)
    result = "TÀI" if (score >= 50 and vote_sum >= -1) or vote_sum >= max(2, len(used)//4) else "XỈU"

    d1 = ((b[0] + b[min(5,L-1)] + h[7] + layers[8] + xor) % 6) + 1
    d2 = ((b[min(7,L-1)] ^ b[min(11,L-1)] ^ h[29] ^ layers[5] ^ rot) % 6) + 1
    d3 = ((b[-1] + b[min(3,L-1)] + h[53] + layers[6] + layers[9]) % 6) + 1
    total = d1 + d2 + d3
    if result == "TÀI" and total < 11:
        need = 11-total; d3 = min(6, d3+need); total = d1+d2+d3
    if result == "XỈU" and total > 10:
        need = total-10; d3 = max(1, d3-need); total = d1+d2+d3

    agree = abs(vote_sum) / max(1, len(used))
    distance = abs(score - 50)
    if level == "free": base, cap, mul = 52, 78, .30
    elif level == "basic": base, cap, mul = 60, 90, .48
    else: base, cap, mul = 66, 98, .64
    conf = min(cap, base + int(distance*mul) + int(agree*17) + (layers[9] % (5 if level!="free" else 3)))
    parity = (raw + total*47 + xor*13 + rot + h[0] + layers[7]) % 100
    chanle = "CHẴN" if parity >= 50 else "LẺ"
    risk, risk_emoji = _risk(b, raw, layers[9] + xor + rot)
    if vote_sum >= max(4, len(used)//2): trend = "Hội đồng cầu nghiêng Tài"
    elif vote_sum <= -max(4, len(used)//2): trend = "Hội đồng cầu nghiêng Xỉu"
    elif score >= 58: trend = "Điểm hash nghiêng Tài"
    elif score <= 42: trend = "Điểm hash nghiêng Xỉu"
    else: trend = "Cầu cân bằng / nên đi vốn nhỏ"

    return {
        "engine": {"free":"FREE V30 LITE-CAU", "basic":"BASIC V30 OMNI-CAU", "pro":"PRO V30 HITCLUB SHA512/SHA3/BLAKE"}.get(level, "V30"),
        "taixiu": result, "tx_conf": int(conf), "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}", "total": total, "risk": risk, "risk_emoji": risk_emoji,
        "score": round(score,2), "hash_short": s[:8].upper()+"..."+s[-8:].upper(), "trend": trend,
        "details": ["Cầu bệt", "Cầu đảo", "Cầu 1-1", "Cầu 2-1", "Cầu 3-1", "Mirror", "Đầu/đuôi", "Chẵn/lẻ", "Byte wave", "Entropy", "Multi-hash vote"][: (6 if level=='free' else 9 if level=='basic' else 11)]
    }

def predict_free(hash_hex, gate_key=""):
    return _core(hash_hex, gate_key, "free")

def predict_basic(hash_hex):
    return _core(hash_hex, "", "basic")

def predict_pro(hash_hex, gate_key=""):
    return _core(hash_hex, gate_key, "pro")
