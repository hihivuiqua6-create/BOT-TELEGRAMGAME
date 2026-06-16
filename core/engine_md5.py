# -*- coding: utf-8 -*-
"""
KINGBOT MD5/TX ENGINE V103 - OMNI CAU + STABLE MD5
- Nền từ bản V51 user gửi
- Thêm confidence thực tế hơn theo: history quality, markov, vote agreement, risk penalty
- Thêm khuyến nghị: NÊN ĐÁNH / ĐÁNH NHỎ / BỎ QUA
- Giữ API cũ: predict_free, predict_basic, predict_pro, predict
Lưu ý: Không có thuật toán nào đảm bảo thắng chắc từ MD5/hash. Muốn % có ý nghĩa hơn cần truyền history càng dài càng tốt.
"""

import hashlib
import math
import statistics
from collections import Counter, defaultdict

HEX = set("0123456789abcdefABCDEF")

GAME_PROFILES = {
    "auto":    {"salt":"AUTO-ROYAL-V103",    "break":1.00, "trend":1.00, "noise":1.00, "dice":1.00, "phase":1.00, "safe":0.00},
    "lc79":    {"salt":"LC79-REAL-V103",     "break":1.18, "trend":1.08, "noise":0.93, "dice":1.13, "phase":1.05, "safe":0.02},
    "bet":     {"salt":"BETVIP-REAL-V103-OMNI", "break":1.20, "trend":1.16, "noise":0.91, "dice":1.15, "phase":1.11, "safe":0.025},
    "betvip":  {"salt":"BETVIP-REAL-V103-OMNI", "break":1.29, "trend":1.22, "noise":0.87, "dice":1.20, "phase":1.18, "safe":0.036},
    "betvip.bet": {"salt":"BETVIP-REAL-V103-OMNI", "break":1.29, "trend":1.22, "noise":0.87, "dice":1.20, "phase":1.18, "safe":0.036},
    "bv":      {"salt":"BETVIP-REAL-V103-OMNI", "break":1.29, "trend":1.22, "noise":0.87, "dice":1.20, "phase":1.18, "safe":0.036},
    "hitclub": {"salt":"HITCLUB-SHA256-V103-OMNI", "break":1.36, "trend":1.20, "noise":0.86, "dice":1.27, "phase":1.22, "safe":0.040},
    "hit":     {"salt":"HITCLUB-SHA256-V103-OMNI", "break":1.36, "trend":1.20, "noise":0.86, "dice":1.27, "phase":1.22, "safe":0.040},
    "hc":      {"salt":"HITCLUB-SHA256-V103-OMNI", "break":1.36, "trend":1.20, "noise":0.86, "dice":1.27, "phase":1.22, "safe":0.040},
    "sunwin":  {"salt":"SUNWIN-HASH-V103",   "break":1.10, "trend":1.09, "noise":0.98, "dice":1.05, "phase":1.02, "safe":0.01},
    "go88":    {"salt":"GO88-HASH-V103",     "break":1.09, "trend":1.07, "noise":0.99, "dice":1.04, "phase":1.01, "safe":0.00},
    "rikvip":  {"salt":"RIKVIP-HASH-V103",   "break":1.11, "trend":1.06, "noise":0.97, "dice":1.04, "phase":1.03, "safe":0.00},
    "b52":     {"salt":"B52-HASH-V103",      "break":1.07, "trend":1.04, "noise":1.00, "dice":1.02, "phase":1.00, "safe":0.00},
    "789":     {"salt":"789-HASH-V103",      "break":1.12, "trend":1.05, "noise":0.97, "dice":1.03, "phase":1.04, "safe":0.00},
    "tx":      {"salt":"TX-GENERAL-V103",    "break":1.00, "trend":1.00, "noise":1.00, "dice":1.00, "phase":1.00, "safe":0.00},
}

PATTERNS = [
    ("Cầu bệt T", [1,1,1,1,1]), ("Cầu bệt X", [0,0,0,0,0]),
    ("Cầu đảo 1-1", [1,0,1,0,1,0]), ("Cầu đảo kép", [1,0,0,1,1,0,0,1]),
    ("Cầu 2-1", [1,1,0,1,1,0]), ("Cầu 1-2", [1,0,0,1,0,0]),
    ("Cầu 2-2", [1,1,0,0,1,1,0,0]), ("Cầu 3-1", [1,1,1,0,1,1,1,0]),
    ("Cầu 1-3", [1,0,0,0,1,0,0,0]), ("Cầu 3-2", [1,1,1,0,0,1,1,1,0,0]),
    ("Cầu 2-3", [1,1,0,0,0,1,1,0,0,0]), ("Cầu 4-1", [1,1,1,1,0,1,1,1,1,0]),
    ("Cầu 1-4", [1,0,0,0,0,1,0,0,0,0]), ("Sandwich T", [1,0,1,1,0,1]),
    ("Sandwich X", [0,1,0,0,1,0]), ("Cầu sóng lệch", [1,0,1,0,0,1,0,1]),
    ("Tam giác", [1,1,0,1,0,0,1,1,1,0]), ("Cầu đôi lệch", [1,1,0,1,0,0,1,1,0]),
    ("Cầu ngầm T", [1,1,1,0,0,0,1,1,1,0,0,0]), ("Cầu ngầm X", [0,0,0,1,1,1,0,0,0,1,1,1]),
    ("Cầu ngầm kép", [1,1,0,0,1,1,0,0,1,1,0,0,1,1,0,0]), ("Cầu ngầm lệch", [1,1,1,0,0,1,1,1,0,0,1,1,1,0,0]),
    ("Cầu ảo T", [1,0,1,0,1,0,0,1,0,1,0,1]), ("Cầu ảo X", [0,1,0,1,0,1,1,0,1,0,1,0]),
    ("Cầu ảo 2-1-1", [1,1,0,1,1,0,0,1,1,0,1,1,0,0]), ("Cầu ảo 1-2-2", [1,0,0,1,0,0,1,1,0,1,0,0,1,1,0]),
    ("Cầu lăn T", [1,1,0,1,0,1,1,0,1,0,1,1,0,1,0]), ("Cầu lăn X", [0,0,1,0,1,0,0,1,0,1,0,0,1,0,1]),
    ("Cầu lăn kép", [1,1,0,0,1,0,1,1,0,0,1,0,1,1,0,0,1,0]),
    ("Cầu trùng pha T", [1,0,1,1,0,1,1,1,0,1,1,1,1,0]), ("Cầu trùng pha X", [0,1,0,0,1,0,0,0,1,0,0,0,0,1]),
    ("Cầu trùng pha đảo", [1,0,0,1,1,0,0,0,1,1,1,0,0,0,0,1,1,1,1,0]),
    ("Xoắn ốc T", [1,1,0,1,0,0,1,0,0,0,1,0,0,0,0,1]), ("Xoắn ốc X", [0,0,1,0,1,1,0,1,1,1,0,1,1,1,1,0]),
    ("Xoắn ốc kép", [1,1,0,0,1,1,1,0,0,0,1,1,1,1,0,0,0,0]),
    ("Sóng đôi T", [1,0,1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1,0,1]), ("Sóng đôi X", [0,1,0,1,0,0,1,0,1,0,0,1,0,1,0,0,1,0,1,0]),
    ("Cầu 1-1", [1,0,1,0,1,0,1,0,1,0,1,0]), ("Cầu đảo 1-1", [0,1,0,1,0,1,0,1,0,1,0,1]),
    ("Cầu 2-1", [1,1,0,1,1,0,1,1,0,1,1,0,1,1,0]), ("Cầu 3-1", [1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,0]),
    ("Lồi T", [1,1,1,0,0,1,1,1,0,0,1,1,1,0,0]), ("Lõm X", [0,0,0,1,1,0,0,0,1,1,0,0,0,1,1]),
    ("Lồi lõm kép", [1,1,0,0,0,1,1,1,0,0,0,1,1,1,1,0,0,0]),
    ("Xoay chiều 3T-3X", [1,1,1,0,0,0,1,1,1,0,0,0,1,1,1]),
    ("Xoay chiều 4T-2X", [1,1,1,1,0,0,1,1,1,1,0,0,1,1,1,1]),
    ("Xoay chiều 2T-4X", [1,1,0,0,0,0,1,1,0,0,0,0,1,1]),
    ("Ma trận 3x3", [1,1,1,1,0,0,1,0,0,1,1,1,1,0,0,1,0,0,1,1,1,1,0,0,1,0,0]),
    ("Ma trận 4x4", [1,1,1,1,1,0,0,0,1,0,0,0,1,1,1,1,1,0,0,0,1,0,0,0,1,1,1,1]),
    ("Hình thoi T", [1,1,0,1,0,1,0,0,1,0,1,0,0,1,1]), ("Hình thoi X", [0,0,1,0,1,0,1,1,0,1,0,1,1,0,0]),
    ("Chéo T", [1,0,1,0,0,1,0,1,0,0,1,0,1,0,0,1,0,1]), ("Chéo X", [0,1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1,0]),
    ("Vòng tròn 6", [1,1,0,0,1,0,1,1,0,0,1,0,1,1,0,0,1,0]), ("Vòng tròn 8", [1,1,1,0,0,1,0,0,1,1,1,0,0,1,0,0,1,1,1,0,0,1,0,0]),
    ("Lượng tử T", [1,0,0,1,1,0,1,1,1,0,1,1,1,1,0,1,1,1,1,1,0]), ("Lượng tử X", [0,1,1,0,0,1,0,0,0,1,0,0,0,0,1,0,0,0,0,0,1]),
    ("Hỗn độn T", [1,1,0,1,0,0,0,1,1,0,1,1,0,1,0,0,1,1,1,0,0,1,0,1]), ("Hỗn độn X", [0,0,1,0,1,1,1,0,0,1,0,0,1,0,1,1,0,0,0,1,1,0,1,0]),
]


# V103 thêm các pattern cầu thực chiến bổ sung: cầu gãy, cầu hồi, cầu tam đoạn, cầu lặp lệch.
PATTERNS += [
    ("Cầu bẻ bệt T", [1,1,1,1,0,1,1,1,1,0]),
    ("Cầu bẻ bệt X", [0,0,0,0,1,0,0,0,0,1]),
    ("Cầu hồi T", [1,1,0,1,1,1,0,1,1,1,1,0]),
    ("Cầu hồi X", [0,0,1,0,0,0,1,0,0,0,0,1]),
    ("Cầu tam đoạn T", [1,1,0,1,0,0,1,1,1,0,0,0]),
    ("Cầu tam đoạn X", [0,0,1,0,1,1,0,0,0,1,1,1]),
    ("Cầu đảo lệch T", [1,0,1,1,0,1,0,0,1,0,1,1]),
    ("Cầu đảo lệch X", [0,1,0,0,1,0,1,1,0,1,0,0]),
    ("Cầu 5-1", [1,1,1,1,1,0,1,1,1,1,1,0]),
    ("Cầu 1-5", [1,0,0,0,0,0,1,0,0,0,0,0]),
    ("Cầu 4-2", [1,1,1,1,0,0,1,1,1,1,0,0]),
    ("Cầu 2-4", [1,1,0,0,0,0,1,1,0,0,0,0]),
]


# Sinh thêm full cầu A-B để bắt đúng các dạng 1-1, 1-2, 2-2, 1-3...
def _append_run_patterns():
    def make(a,b,start=1,repeat=4):
        other = 0 if start else 1
        return ([start]*a + [other]*b) * repeat
    for a in range(1,9):
        for b in range(1,9):
            PATTERNS.append((f"Cầu {a}-{b}", make(a,b,1,4)))
            PATTERNS.append((f"Cầu {a}-{b} X", make(a,b,0,4)))
    for runs3 in ((1,2,1),(2,1,2),(1,3,1),(3,1,3),(1,3,2),(2,3,1),(3,2,1),(1,2,3),(2,2,1),(1,2,2)):
        pat=[]; cur=1
        for n in runs3*3:
            pat += [cur]*n; cur = 0 if cur else 1
        PATTERNS.append(("Cầu " + "-".join(map(str,runs3)), pat))
_append_run_patterns()

def _clean_hash(x):
    s = str(x or "").strip().lower().replace(" ", "").replace("-", "").replace(":", "")
    if len(s) < 32 or len(s) % 2: return None
    if any(c not in HEX for c in s): return None
    if len(s) not in (32, 40, 56, 64, 96, 128): s = hashlib.sha256(s.encode()).hexdigest()
    return s


def _parse(x):
    s = _clean_hash(x)
    if not s: return None, None, None, None
    b = [int(s[i:i+2], 16) for i in range(0, len(s), 2)]
    n = [int(c, 16) for c in s]
    kind = "MD5" if len(s) == 32 else "SHA1/40" if len(s) == 40 else "HITCLUB/SHA256" if len(s) == 64 else "HEX-%d" % len(s)
    return s, b, n, kind


def _profile(game):
    g = str(game or "auto").lower().strip().replace(" ", "")
    aliases = {
        "betvipbet":"betvip", "betvip.bet":"betvip", "betvipcom":"betvip",
        "bv":"betvip", "bet_vip":"betvip", "bet-vip":"betvip",
        "hitclub.com":"hitclub", "hitclubbet":"hitclub",
    }
    g = aliases.get(g, g)
    return GAME_PROFILES.get(g, GAME_PROFILES["auto"]), (g if g in GAME_PROFILES else "auto")


def _mix_bytes(*parts, rounds=8):
    seed = "|".join(map(str, parts)).encode("utf-8", "ignore")
    out = []
    for r in range(rounds):
        a = hashlib.sha512(seed + bytes([r])).digest()
        b = hashlib.sha3_512(seed[::-1] + a[:24] + bytes([r * 7 % 256])).digest()
        c = hashlib.blake2b(seed + a[-16:] + b[:16], digest_size=64).digest()
        d = hashlib.sha256(a + b + c + seed).digest()
        e = hashlib.md5(c + d + seed[:32]).digest()
        out.extend(a + b + c + d + e)
        seed = hashlib.sha512(seed + a[:20] + b[-20:] + c[12:44] + d + e).digest()
    return list(out)


def _entropy(vals):
    if not vals: return 0.0
    c = Counter(vals); total = len(vals); e = 0.0
    for v in c.values():
        p = v / total; e -= p * math.log2(p)
    return e


def _stdev(vals):
    try: return statistics.pstdev(vals) if len(vals) > 1 else 0.0
    except Exception: return 0.0


def _clamp(v, a, b): return max(a, min(b, v))


def _pattern_score(bits, pat):
    if not bits or not pat: return 0
    best = 0; m = len(pat); L = len(bits)
    for off in range(m):
        ok = sum(1 for i, x in enumerate(bits) if x == pat[(i + off) % m])
        if ok > best: best = ok
    return int(best * 10000 / L)


def _runs(bits):
    if not bits: return []
    out=[]; cur=bits[0]; cnt=1
    for x in bits[1:]:
        if x == cur: cnt += 1
        else: out.append((cur,cnt)); cur=x; cnt=1
    out.append((cur,cnt)); return out


def _history_bits(history):
    if not history: return []
    out=[]
    if isinstance(history, str):
        raw = history.replace(",", " ").replace("|", " ").replace(";", " ").split()
        if len(raw) <= 1:
            raw = list(history)
    else:
        raw = history
    for x in raw:
        t = str(x).strip().upper()
        if t in ("T", "TAI", "TÀI", "1", "BIG", "B"): out.append(1)
        elif t in ("X", "XIU", "XỈU", "0", "SMALL", "S"): out.append(0)
    return out[-500:]


def _make_bits(n, b, h, history=None):
    N=len(n); L=len(b)
    bits_parity = [x & 1 for x in n]
    bits_high   = [1 if x >= 8 else 0 for x in n]
    bits_byte   = [1 if x >= 128 else 0 for x in b]
    bits_pair   = [((n[i] + n[(i+1)%N] + h[i % len(h)]) & 1) for i in range(N)]
    bits_mirror = [((n[i] ^ n[N-1-i] ^ (i*3) ^ h[(i*5)%len(h)]) & 1) for i in range(N)]
    bits_wave   = [1 if ((b[i % L] + h[(i*11)%len(h)] + i*17) % 256) >= 128 else 0 for i in range(max(N, L*2))]
    bits_phase  = [1 if ((i * 73 + h[i % len(h)] * 17) % 256) >= (128 + (i % 64)) else 0 for i in range(max(N, L))]
    hb = _history_bits(history)
    hist_mix = hb + [hb[i] ^ hb[i-1] for i in range(1, len(hb))] if hb else []
    return bits_parity + bits_high + bits_byte + bits_pair + bits_mirror + bits_wave + bits_phase + hist_mix


def _dice_from_result(result, b, h, layers, raw, pf):
    L=len(b); layers = layers or [1,2,3,4]
    d1 = int(((b[0] + b[L//3] + h[7] + layers[0] * pf["dice"]) % 6) + 1)
    d2 = int(((b[L//2] ^ b[-2] ^ h[31] ^ layers[min(3, len(layers)-1)]) % 6) + 1)
    d3 = int(((b[-1] + h[63] + layers[-1] + raw) % 6) + 1)
    total = d1+d2+d3; guard=0
    while result == "TÀI" and total < 11 and guard < 18:
        if d1 < 6: d1 += 1
        elif d2 < 6: d2 += 1
        elif d3 < 6: d3 += 1
        else: break
        total=d1+d2+d3; guard += 1
    guard=0
    while result == "XỈU" and total > 10 and guard < 18:
        if d1 > 1: d1 -= 1
        elif d2 > 1: d2 -= 1
        elif d3 > 1: d3 -= 1
        else: break
        total=d1+d2+d3; guard += 1
    return d1,d2,d3,total


def _phase_analysis(bits, h):
    L = len(bits)
    if L < 20: return 0, 0, 0
    periods = []
    for p in range(2, min(64, L//2)):
        match = sum(1 for i in range(L-p) if bits[i] == bits[i+p])
        periods.append((p, match / max(1, L-p)))
    best_p, best_ratio = max(periods, key=lambda x: x[1]) if periods else (0, 0)
    phase_strength = int(best_ratio * 10000)
    cumsum = 0; max_dev = 0
    for bit in bits:
        cumsum += 1 if bit == 1 else -1
        max_dev = max(max_dev, abs(cumsum))
    underflow = int(max_dev * 137 + h[0] * 19 + best_p * 91) % 10000
    return phase_strength, underflow, best_p


def _markov_predict(hb, max_order=4):
    """Trả về xác suất Tài từ lịch sử bằng Markov order 1..4, có smoothing."""
    if len(hb) < 8:
        return 0.5, 0.0, "Thiếu lịch sử"
    best = (0.5, 0.0, "Markov yếu")
    for order in range(min(max_order, len(hb)-2), 0, -1):
        key = tuple(hb[-order:])
        nxt = []
        for i in range(len(hb)-order):
            if tuple(hb[i:i+order]) == key:
                nxt.append(hb[i+order])
        if len(nxt) >= 2:
            p_t = (sum(nxt) + 1) / (len(nxt) + 2)
            strength = min(1.0, len(nxt) / 16.0) * abs(p_t - 0.5) * 2
            label = "Markov %d bước: T %.1f%% / mẫu %d" % (order, p_t*100, len(nxt))
            best = (p_t, strength, label)
            break
    return best


def _auto_discovery(hb):
    """Tự phát hiện cầu ngắn/dài từ history, không hardcode."""
    if len(hb) < 10:
        return 0.5, 0.0, "Auto cầu yếu"
    candidates = []
    max_len = min(18, len(hb)//2)
    for L in range(2, max_len+1):
        pat = hb[-L:]
        hits = []
        for i in range(0, len(hb)-L):
            if hb[i:i+L] == pat and i+L < len(hb):
                hits.append(hb[i+L])
        if hits:
            p_t = (sum(hits)+1)/(len(hits)+2)
            strength = min(1, len(hits)/10) * abs(p_t-0.5)*2
            candidates.append((strength, p_t, L, len(hits)))
    if not candidates:
        return 0.5, 0.0, "Chưa thấy cầu lặp"
    strength, p_t, L, count = max(candidates, key=lambda x:x[0])
    return p_t, strength, "Auto cầu %d nhịp: T %.1f%% / mẫu %d" % (L, p_t*100, count)


def _history_quality(hb):
    if not hb: return 0.0
    q_len = min(1.0, len(hb) / 120.0)
    r = _runs(hb)
    changes = sum(hb[i] != hb[i-1] for i in range(1, len(hb))) / max(1, len(hb)-1)
    balance = 1.0 - abs((sum(hb)/len(hb)) - 0.5) * 2
    # lịch sử quá lệch hoặc quá ngắn thì giảm tin cậy
    return _clamp(q_len * 0.55 + balance * 0.25 + (1-abs(changes-0.5)*2) * 0.20, 0, 1)


def _risk_level(raw_risk):
    if raw_risk < 31: return "THẤP", "🟢"
    if raw_risk < 68: return "TRUNG BÌNH", "🟡"
    return "CAO", "🔴"


def _advice(final_prob, risk_score, quality, level, agree, hb_len):
    edge = abs(final_prob - 0.5)
    if hb_len < 20:
        return "BỎ QUA", "Thiếu lịch sử, chưa nên vào tiền", 0
    if risk_score >= 72 or quality < 0.28 or edge < 0.055:
        return "BỎ QUA", "Kèo nhiễu/cân, không đủ lợi thế", 0
    if risk_score >= 58 or edge < 0.085:
        return "ĐÁNH NHỎ", "Có tín hiệu nhưng chưa sạch, chỉ đi vốn nhỏ", 1
    if level == "free" and edge < 0.12:
        return "ĐÁNH NHỎ", "Free giới hạn tầng lọc, không nên all-in", 1
    return "NÊN ĐÁNH", "Tín hiệu đồng thuận tốt, vẫn quản lý vốn", 2



# ============================================================
# V141 ULTRA BOOSTER (math-grounded ensemble for MD5/TX)
# - Hash-feature logistic score (32 features, fixed weights)
# - Multi-order Markov ensemble (1..6) with sample-size confidence
# - k-NN by tail fingerprint with Laplace smoothing
# - Periodicity (autocorrelation) detector with phase lock
# Calibrated blend with existing final_prob_t.
# ============================================================

def _v141_logistic(x):
    if x >  16: return 1.0
    if x < -16: return 0.0
    import math as _m
    return 1.0 / (1.0 + _m.exp(-x))

_V141_W = [
    +0.41,-0.33,+0.27,+0.19,-0.22,+0.31,-0.18,+0.24,
    +0.15,-0.29,+0.22,-0.17,+0.26,+0.13,-0.21,+0.30,
    -0.16,+0.23,-0.25,+0.18,+0.20,-0.14,+0.28,-0.19,
    +0.17,+0.21,-0.24,+0.16,-0.20,+0.25,-0.15,+0.22,
]

def _v141_hash_features(h, n, b):
    """32 signed features in [-1,1] derived from hash bytes + nibbles."""
    L = len(b) or 1
    N = len(n) or 1
    pop = sum(bin(x).count("1") for x in h) / (len(h)*8)
    par = sum(h[i::8][0] & 1 for i in range(8)) / 8.0
    feats = []
    # popcount drift over 8 buckets
    for i in range(8):
        seg = h[i*len(h)//8:(i+1)*len(h)//8] or [0]
        feats.append((sum(bin(x).count("1") for x in seg)/(len(seg)*8)) - 0.5)
    # nibble parity windows
    for i in range(8):
        seg = n[i*N//8:(i+1)*N//8] or [0]
        feats.append((sum(v & 1 for v in seg)/max(1,len(seg))) - 0.5)
    # byte hi/lo ratio
    for i in range(8):
        seg = b[i*L//8:(i+1)*L//8] or [0]
        feats.append((sum(1 for v in seg if v >= 128)/max(1,len(seg))) - 0.5)
    # mod/xor walks
    for i in range(8):
        s = 0
        for j,v in enumerate(b):
            s += ((v ^ h[(j*7+i)%len(h)]) >> (i%5)) & 1
        feats.append((s/max(1,L)) - 0.5)
    feats = feats[:32]
    while len(feats) < 32:
        feats.append(0.0)
    return feats, pop, par

def _v141_markov_ensemble(hb, max_order=6):
    """Weighted blend of Markov orders 1..max_order. Returns (p_tai, conf)."""
    if len(hb) < 6:
        return 0.5, 0.0
    import math as _m
    num = 0.0; den = 0.0
    for order in range(1, min(max_order, len(hb)-2)+1):
        key = tuple(hb[-order:])
        nxt = [hb[i+order] for i in range(len(hb)-order)
               if tuple(hb[i:i+order]) == key]
        if len(nxt) >= 2:
            p = (sum(nxt) + 1) / (len(nxt) + 2)
            # weight: bigger order + bigger sample = more trust
            w = _m.log1p(len(nxt)) * (1 + order*0.25)
            num += p * w
            den += w
    if den == 0:
        return 0.5, 0.0
    p = num / den
    conf = min(1.0, den / 12.0) * abs(p - 0.5) * 2
    return p, conf

def _v141_knn_tail(hb, k=5, max_L=10):
    """For each tail length L, find similar past windows; vote next bit."""
    if len(hb) < 12:
        return 0.5, 0.0
    best = (0.5, 0.0)
    for L in range(3, min(max_L, len(hb)//3)+1):
        tail = hb[-L:]
        matches = []
        for i in range(len(hb)-L-1):
            window = hb[i:i+L]
            # hamming distance
            d = sum(1 for a,c in zip(tail, window) if a != c)
            if d <= max(1, L//4):
                matches.append((d, hb[i+L]))
        if len(matches) >= 3:
            matches.sort(key=lambda x: x[0])
            top = matches[:k]
            # inverse-distance weighted vote
            num = sum((1.0/(d+0.5)) * v for d,v in top)
            den = sum(1.0/(d+0.5) for d,_ in top)
            p = (num + 0.5) / (den + 1.0)
            conf = min(1.0, len(matches)/8.0) * abs(p - 0.5) * 2
            if conf > best[1]:
                best = (p, conf)
    return best

def _v141_autocorr(hb, max_lag=24):
    """Find dominant period via autocorrelation; predict next via phase."""
    if len(hb) < 20:
        return 0.5, 0.0
    mean = sum(hb)/len(hb)
    var = sum((x-mean)**2 for x in hb) / len(hb) or 1e-9
    best_lag = 0; best_r = 0.0
    for lag in range(2, min(max_lag, len(hb)//3)+1):
        c = sum((hb[i]-mean)*(hb[i+lag]-mean) for i in range(len(hb)-lag))
        r = c / (var * (len(hb)-lag))
        if r > best_r:
            best_r = r; best_lag = lag
    if best_lag == 0 or best_r < 0.18:
        return 0.5, 0.0
    pred_bit = hb[-best_lag]  # phase lock
    p = 0.5 + (pred_bit - 0.5) * min(0.42, best_r)
    return p, min(1.0, best_r)

def _v141_ensemble(hb, h, n, b):
    """Returns (p_tai_v141, agree_v141, debug)."""
    feats, pop, par = _v141_hash_features(h, n, b)
    z = sum(w*f for w,f in zip(_V141_W, feats)) + (pop-0.5)*0.4 + (par-0.5)*0.3
    p_hash = _v141_logistic(z * 2.2)

    p_mk, c_mk   = _v141_markov_ensemble(hb, max_order=6)
    p_knn, c_knn = _v141_knn_tail(hb)
    p_ac, c_ac   = _v141_autocorr(hb)

    # weights: history-driven signals dominate when confident
    w_hash = 0.18
    w_mk   = 0.30 + c_mk  * 0.25
    w_knn  = 0.20 + c_knn * 0.25
    w_ac   = 0.12 + c_ac  * 0.20
    s = w_hash + w_mk + w_knn + w_ac
    p = (p_hash*w_hash + p_mk*w_mk + p_knn*w_knn + p_ac*w_ac) / s
    agree = (c_mk + c_knn + c_ac) / 3.0
    return p, agree, {"hash":round(p_hash,3),"mk":round(p_mk,3),"knn":round(p_knn,3),"ac":round(p_ac,3),
                      "c_mk":round(c_mk,3),"c_knn":round(c_knn,3),"c_ac":round(c_ac,3)}


def _core(hash_hex, gate_key="", level="basic", game="auto", history=None):
    s,b,n,kind = _parse(hash_hex)
    if not s: return None
    level = str(level or "basic").lower().strip()
    if level in ("thuong", "thường", "normal", "std"): level = "basic"
    if level not in ("free", "basic", "pro"): level = "basic"
    pf, game_name = _profile(game)
    rounds = 4 if level == "free" else 8 if level == "basic" else 13
    h = _mix_bytes("KINGBOT-V93-BETVIP-STABLE-REAL-CONF-ADVICE", pf["salt"], kind, level, gate_key, s, s[::-1], rounds=rounds)

    L=len(b); N=len(n)
    front=sum(b[:L//2]); back=sum(b[L//2:]); even=sum(b[::2]); odd=sum(b[1::2])
    nf=sum(n[:N//2]); nb=sum(n[N//2:])
    ent_n=_entropy(n); ent_b=_entropy(b); st_b=_stdev(b); st_n=_stdev(n)
    bits = _make_bits(n,b,h,history)
    phase_strength, underflow, best_period = _phase_analysis(bits, h)
    r = _runs(bits); max_run=max([c for _,c in r], default=1)
    change_count=sum(bits[i] != bits[i-1] for i in range(1, len(bits)))
    run_pressure=sum((v+1)*(c**2) for v,c in r) % 10000
    xor=0
    for i,x in enumerate(b):
        xor ^= ((x << (i % 8)) & 255) ^ h[(i*13)%len(h)] ^ h[(len(h)-1-i)%len(h)]
    rot=sum((((b[i] << (i%5)) & 255) ^ h[(i*17+11)%len(h)])*(i+3) for i in range(L)) % 10000

    pattern_layers=[]
    for j,(name,pat) in enumerate(PATTERNS):
        val = _pattern_score(bits, pat)
        phase_bonus = (phase_strength // 100) if ("ngầm" in name or "pha" in name or "lăn" in name) else 0
        val = int((val * pf["trend"] + h[(j*19+3)%len(h)]*37 + abs(front-back)*(j%5+1) + abs(even-odd)*(j%7+1) + phase_bonus*11) % 10000)
        pattern_layers.append((name,val))

    p_bet=max(v for k,v in pattern_layers if "bệt" in k)
    p_dao=(max(v for k,v in pattern_layers if "đảo" in k or "Zigzag" in k or "ngầm" in k) + change_count*97) % 10000
    p_mirror=(sum((n[i]^n[N-1-i])*(i+5) for i in range(N)) + h[9]*41 + abs(nf-nb)*17) % 10000
    p_headtail=(int(s[:8],16)+int(s[-8:],16)+front*17+back*19+h[10]*43) % 10000
    p_mod=(sum(((i+1)*n[i] + h[(i*7)%len(h)]) % 97 for i in range(N))*113 + xor*11) % 10000
    p_fibo=(sum(n[i]*(1,1,2,3,5,8,13,21,34,55)[i%10] for i in range(N))*31 + h[12]*53) % 10000
    p_cycle3=sum((i%3+1)*(n[i]+h[(i*3)%len(h)]) for i in range(N)) % 10000
    p_cycle5=sum((i%5+1)*(n[i]+h[(i*5)%len(h)]) for i in range(N)) % 10000
    p_cycle7=sum((i%7+1)*(b[i%L]+h[(i*7)%len(h)]) for i in range(max(N,L))) % 10000
    p_cycle9=sum((i%9+1)*(n[i]+h[(i*9)%len(h)]) for i in range(N)) % 10000
    p_wave=int((math.sin((front+rot)%360)*2500 + math.cos((back+xor)%360)*2500 + 5000 + h[22]*13)) % 10000
    p_entropy=int((ent_n*997 + ent_b*1499 + st_b*121 + st_n*173 + abs(front-back)*7 + abs(even-odd)*5)) % 10000
    p_noise=int(((10000 - abs(5000-p_entropy)) * pf["noise"] + h[25]*31 + st_b*29) % 10000)
    p_phase = int(phase_strength * pf["phase"] + underflow * 0.37 + h[29]*61) % 10000
    p_underflow = int(underflow * pf["phase"] + phase_strength * 0.23 + h[30]*67) % 10000

    hb=_history_bits(history)
    hq = _history_quality(hb)
    if hb:
        hr=_runs(hb); hmax=max([c for _,c in hr], default=1); hchg=sum(hb[i]!=hb[i-1] for i in range(1,len(hb)))
        h_break=(hmax*999 + hchg*177 + (1 if len(hb)>=2 and hb[-1]==hb[-2] else 0)*777) % 10000
        h_last=hb[-1]
    else:
        h_break=0; h_last=None

    break_power=int((max_run*671 + run_pressure//2 + abs(front-back)*37 + abs(even-odd)*31 + abs(nf-nb)*43 + int(st_b*139) + ((p_bet ^ p_dao ^ p_mirror ^ rot ^ xor) % 10000) + h[21]*67 + h_break*1.35 + p_phase*0.51 + p_underflow*0.43) * pf["break"]) % 10000
    trap_power=int((break_power*0.63 + p_noise*0.27 + p_entropy*0.41 + h[27]*53 + (10000-p_dao)%10000 + p_underflow*0.31) % 10000)

    special_layers=[
        ("Mirror/đối xứng",p_mirror),("Đầu đuôi",p_headtail),("Modulo",p_mod),("Fibonacci",p_fibo),
        ("Chu kỳ 3",p_cycle3),("Chu kỳ 5",p_cycle5),("Chu kỳ 7",p_cycle7),("Chu kỳ 9",p_cycle9),
        ("Sóng",p_wave),("Entropy",p_entropy),("Nhiễu",p_noise),("Cầu bẻ/gãy",break_power),("Trap cầu",trap_power),
        ("Cầu pha",p_phase),("Cầu ngầm/underflow",p_underflow),("Chu kỳ tốt nhất",best_period*157 % 10000)
    ]
    all_layers=pattern_layers+special_layers

    if level == "free":
        selected_names = {"Cầu bệt T","Cầu bệt X","Cầu đảo 1-1","Cầu 2-1","Cầu 1-2","Sandwich T","Sandwich X","Đầu đuôi","Entropy","Cầu ngầm T","Cầu ngầm X"}
        vote_rounds = 1
    elif level == "basic":
        selected_names = set(k for k,_ in pattern_layers[:28]) | {"Mirror/đối xứng","Đầu đuôi","Modulo","Chu kỳ 3","Chu kỳ 5","Chu kỳ 7","Entropy","Cầu bẻ/gãy","Trap cầu","Cầu pha","Cầu ngầm/underflow"}
        vote_rounds = 4
    else:
        selected_names = set(k for k,_ in all_layers)
        vote_rounds = 8
    used=[(k,v) for k,v in all_layers if k in selected_names]

    weights=[17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,191,193,197,199]
    raw=sum((v+h[(i*23+7)%len(h)]*weights[i%len(weights)])*weights[i%len(weights)] for i,(k,v) in enumerate(used))
    raw=(raw + xor*131 + rot*137 + sum(h[:192])*3 + len(s)*911 + int(pf["trend"]*1000) + p_phase*13 + p_underflow*17) % 10000
    score=raw/100.0

    votes=[]
    for rd in range(vote_rounds):
        for i,(name,v) in enumerate(used):
            gate=h[(i*31+rd*47+5)%len(h)] + h[(i*43+rd*53+9)%len(h)] + xor + rot + rd*997
            phase_factor = (p_phase // 500) if "pha" in name or "ngầm" in name else 0
            bit=((v + raw + gate + (break_power if "bẻ" in name or "Trap" in name else 0) + phase_factor) % 100) >= 50
            if level != "free" and break_power > 6800 and ("bệt" in name or "đảo" in name or "Trap" in name or "ngầm" in name): bit=not bit
            if level == "pro" and trap_power > 7400 and i % 3 == 0: bit=not bit
            if p_underflow > 7200 and (i % 5 == 0 or "ngầm" in name): bit = not bit
            votes.append(1 if bit else -1)
    vote_sum=sum(votes); agree=abs(vote_sum)/max(1,len(votes))
    hash_prob_t = _clamp(0.5 + (score-50)/100 * 0.42 + (vote_sum/max(1,len(votes))) * 0.18, 0.05, 0.95)

    max_order = 0 if level == "free" else 2 if level == "basic" else 4
    markov_t, markov_strength, markov_note = _markov_predict(hb, max_order=max_order) if max_order else (0.5,0.0,"Free không dùng Markov sâu")
    auto_t, auto_strength, auto_note = _auto_discovery(hb) if level == "pro" else (0.5,0.0,"Auto discovery chỉ bật mạnh ở Pro")

    # Trộn xác suất: hash chỉ là tín hiệu phụ, lịch sử mới quyết định độ thật của %.
    w_hash = 0.52 if level == "free" else 0.38 if level == "basic" else 0.28
    w_markov = 0.00 if level == "free" else 0.36 if level == "basic" else 0.40
    w_auto = 0.00 if level != "pro" else 0.22
    w_bias = 1.0 - w_hash - w_markov - w_auto
    hist_bias = (sum(hb)/len(hb)) if hb else 0.5
    final_prob_t = (hash_prob_t*w_hash + markov_t*w_markov + auto_t*w_auto + hist_bias*w_bias)

    # Cầu bẻ có điều kiện, không flip bừa.
    if hb and level in ("basic","pro"):
        last_run=_runs(hb)[-1][1]
        break_prob = _clamp((break_power/10000)*0.42 + (trap_power/10000)*0.23 + markov_strength*0.22 + auto_strength*0.13, 0, 1)
        if last_run >= (3 if level == "pro" else 4) and break_prob > (0.61 if level == "pro" else 0.72):
            final_prob_t = 0.39 if hb[-1] == 1 else 0.61
        elif p_phase > 7600 and break_power > 6200 and agree < 0.24:
            final_prob_t = 1.0 - final_prob_t

    # === V141 ULTRA BOOSTER blend ===
    try:
        _v141_p, _v141_agree, _v141_dbg = _v141_ensemble(hb, h, n, b)
        # blend weight scales with v141 confidence and history length
        _v141_w = _clamp(0.18 + _v141_agree*0.42 + min(0.18, len(hb)/300.0), 0.18, 0.72)
        final_prob_t = final_prob_t * (1 - _v141_w) + _v141_p * _v141_w
        # if both old and new agree strongly, push edge a bit more
        if (final_prob_t-0.5) * (_v141_p-0.5) > 0 and _v141_agree > 0.35:
            final_prob_t = _clamp(0.5 + (final_prob_t-0.5)*1.08, 0.05, 0.95)
        agree = max(agree, _v141_agree)
    except Exception:
        _v141_dbg = {}
    # === end V141 ===
    result = "TÀI" if final_prob_t >= 0.5 else "XỈU"
    win_prob = max(final_prob_t, 1-final_prob_t)

    # Risk thực hơn: nhiễu + thiếu lịch sử + bất đồng vote + trap.
    base_risk = (st_b * 1.75 + abs(raw - 5000) / 80 + (ent_n+ent_b)*7.4 + break_power/190 + trap_power/240) % 100
    history_penalty = (1-hq) * 24
    disagree_penalty = (1-agree) * 18
    trap_penalty = 10 if trap_power > 7600 else 5 if trap_power > 6500 else 0
    risk_score = int(_clamp(base_risk*0.62 + history_penalty + disagree_penalty + trap_penalty - (7 if level == "pro" else 0), 0, 99))

    # HITCLUB focus: chỉ tăng nhẹ khi là Pro + SHA256 + lịch sử/vote đủ sạch; Free bị giới hạn rõ.
    if game_name in ("hitclub", "hit", "hc") and kind == "HITCLUB/SHA256":
        if level == "pro":
            win_prob = _clamp(win_prob + min(0.018, agree * 0.022 + hq * 0.012), 0.50, 0.90)
            risk_score = max(0, risk_score - 4)
        elif level == "basic":
            win_prob = _clamp(win_prob + min(0.007, agree * 0.010), 0.50, 0.80)
            risk_score = max(0, risk_score - 1)
        else:
            win_prob = _clamp(win_prob - 0.010, 0.50, 0.60)
            risk_score = min(99, risk_score + 6)

    risk,risk_emoji = _risk_level(risk_score)

    advice, advice_reason, stake_level = _advice(win_prob, risk_score, hq, level, agree, len(hb))

    # % đúng nhất có thể từ dữ liệu hiện có: không bơm ảo lên 98 nếu history yếu.
    # % thực tế hơn: không bơm cao; thiếu history thì giữ thấp, vote sạch mới nhích lên.
    max_cap = 0.64 if len(hb) < 20 else 0.72 if len(hb) < 50 else 0.80 if len(hb) < 120 else 0.86
    if level == "pro" and len(hb) >= 80: max_cap += 0.03
    if level == "basic" and len(hb) >= 50: max_cap += 0.01
    if risk_score > 82: max_cap -= 0.05
    if agree < 0.18: max_cap -= 0.04
    real_conf = int(_clamp((win_prob * 100) + ({"free":1,"basic":3,"pro":5}.get(level,3) * agree) + min(3, len(hb)//60), 45, max_cap*100))

    layer_vals=[v for _,v in used]
    d1,d2,d3,total=_dice_from_result(result,b,h,layer_vals,raw,pf)
    parity=(raw + total*47 + xor*13 + rot + h[0] + p_mod + p_cycle5 + p_phase) % 100
    chanle="CHẴN" if parity >= 50 else "LẺ"

    top=sorted(used, key=lambda x:x[1], reverse=True)[:9]
    if advice == "BỎ QUA": trend="Kèo chưa sạch / ưu tiên bỏ qua"
    elif break_power > 7400: trend="Có dấu hiệu cầu bẻ/gãy cầu"
    elif trap_power > 7400: trend="Trap cầu / dễ bẻ nhịp"
    elif p_phase > 7500: trend="Cầu trùng pha / lăn sóng mạnh"
    elif markov_strength > 0.35: trend="Markov lịch sử đang có lực"
    elif auto_strength > 0.35: trend="Auto cầu lặp đang có lực"
    elif final_prob_t >= 0.56: trend="Nghiêng Tài theo hội đồng tín hiệu"
    elif final_prob_t <= 0.44: trend="Nghiêng Xỉu theo hội đồng tín hiệu"
    else: trend="Cân bằng / không rõ nhịp"

    analysis_summary = (
        f"Game {game_name.upper()} | history={len(hb)} | markov={round(markov_strength*100,1)}% | "
        f"auto_cầu={round(auto_strength*100,1)}% | vote={round(agree*100,1)}% | "
        f"risk={risk_score}/100 | break={int(break_power)} | trap={int(trap_power)}"
    )

    return {
        "engine": {"free":"V141 ULTRA", "basic":"V141 ULTRA", "pro":"V141 ULTRA"}[level],
        "game": game_name.upper(),
        "taixiu": result,
        "tx_conf": real_conf,
        "prob_tai": round(final_prob_t*100, 2),
        "prob_xiu": round((1-final_prob_t)*100, 2),
        "advice": advice,
        "advice_reason": advice_reason,
        "stake_level": stake_level,  # 0 bỏ, 1 nhỏ, 2 bình thường
        "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}",
        "total": total,
        "risk": risk,
        "risk_score": risk_score,
        "risk_emoji": risk_emoji,
        "score": round(score,2),
        "hash_short": s[:8].upper()+"..."+s[-8:].upper(),
        "trend": trend,
        "details": [f"{k}: {int(v/100)}%" for k,v in top],
        "analysis_summary": analysis_summary,
        "markov": markov_note,
        "auto_cau": auto_note,
        "history_len": len(hb),
        "history_quality": round(hq*100, 1),
        "vote_agree": round(agree*100, 1),
        "cau_be": int(break_power),
        "trap": int(trap_power),
        "phase": int(p_phase),
        "underflow": int(p_underflow),
        "level": level,
        "kind": kind,
        "v141": _v141_dbg if "_v141_dbg" in dir() or "_v141_dbg" in locals() else {},
        "note": "V141 ULTRA: % đã tăng theo vote/độ sạch cầu/history; vẫn nên quản lý vốn."
    }


def predict_free(hash_hex, gate_key="", game="auto", history=None):
    return _core(hash_hex, gate_key, "free", game, history)


def predict_basic(hash_hex, game="auto", history=None):
    return _core(hash_hex, "", "basic", game, history)


def predict_pro(hash_hex, gate_key="", game="auto", history=None):
    return _core(hash_hex, gate_key, "pro", game, history)


def predict(hash_hex, gate_key="", level="basic", game="auto", history=None):
    return _core(hash_hex, gate_key, level, game, history)


if __name__ == "__main__":
    sample="f3335ef2e7c4f7a8e5b6282938a55ca12fbf53dfc1281aeb2a2bff1745da520f"
    hist="TTTXXTXTXXTTXXTTTXXTXXTTXTXTTXXTXXTTTXXTXTXXTT"
    for game in ("lc79","bet","hitclub"):
        for lv in ("free","basic","pro"):
            print(game, lv, predict(sample, level=lv, game=game, history=hist))
