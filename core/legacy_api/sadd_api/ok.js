const ai = require('../ai_engine');
const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const app = express();
const PORT = process.env.PORT || 3000;

const API_TAIXIU = 'https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=rik&gid=vgmn_100';
const API_MD5 = 'https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=rik&gid=vgmn_101';

const historyCache = {
    taixiu: [],
    taixiumd5: []
};

let lastTaiXiu = null;
let lastTaiXiuMD5 = null;

// 🔥 TRACK SID
let lastSidTaiXiu = null;
let lastSidMD5 = null;

// ===== MARKOV =====
class MarkovXucXac {
    constructor() {
        this.transitions = new Map();
        this.history = [];
    }

    themDuLieu(sequence) {
        this.history = sequence.slice(-10);
        this.transitions.clear();

        for (let i = 0; i < this.history.length - 1; i++) {
            const state = this.history[i];
            const nextState = this.history[i + 1];

            if (!this.transitions.has(state)) {
                this.transitions.set(state, new Map());
            }

            const nextMap = this.transitions.get(state);
            nextMap.set(nextState, (nextMap.get(nextState) || 0) + 1);
        }
    }

    duDoanTiepTheo() {
        if (this.history.length === 0) return Math.floor(Math.random() * 6) + 1;

        const state = this.history[this.history.length - 1];

        if (!this.transitions.has(state)) return Math.floor(Math.random() * 6) + 1;

        const nextMap = this.transitions.get(state);
        let total = 0;
        for (const v of nextMap.values()) total += v;

        let rand = Math.random() * total;
        let sum = 0;

        for (const [k, v] of nextMap) {
            sum += v;
            if (rand <= sum) return k;
        }

        return Math.floor(Math.random() * 6) + 1;
    }
}

// ===== FUNC =====
async function fetchData(url) {
    try {
        const res = await axios.get(url, { timeout: 5000 });
        return res.data;
    } catch {
        return null;
    }
}

function tinhKetQua(d1, d2, d3) {
    const tong = d1 + d2 + d3;
    return {
        tong,
        ket_qua: tong >= 11 ? 'Tài' : 'Xỉu'
    };
}

async function duDoanMarkov(key) {
    const markov = new MarkovXucXac();
    markov.themDuLieu(historyCache[key]);
    const x = markov.duDoanTiepTheo();
    return (x * 3 >= 11) ? 'Tài' : 'Xỉu';
}

// ===== ROUTE TAIXIU =====
app.get('/taixiu', async (req, res) => {
    try {
        const data = await fetchData(API_TAIXIU);

        if (!data || !data.data || data.data.length === 0) {
            return res.json(lastTaiXiu || { error: "API lỗi" });
        }

        const obj = data.data[0];

        const sid = obj.sid;
        const d1 = obj.d1;
        const d2 = obj.d2;
        const d3 = obj.d3;

        // ❌ chưa có sid => bỏ
        if (!sid) {
            return res.json(lastTaiXiu || { error: "Chưa có phiên" });
        }

        // 🔥 sid mới xuất hiện (chưa có xúc xắc)
        if (sid !== lastSidTaiXiu) {
            lastSidTaiXiu = sid;
            return res.json(lastTaiXiu || { wait: "Đang chờ xúc xắc..." });
        }

        // ❌ cùng sid nhưng chưa có xúc xắc
        if (d1 == null || d2 == null || d3 == null) {
            return res.json(lastTaiXiu || { wait: "Chưa có kết quả" });
        }

        // ❌ đã update rồi => không update lại
        if (lastTaiXiu && sid === lastTaiXiu.phien) {
            return res.json(lastTaiXiu);
        }

        // ✅ có đủ data => update
        const { tong, ket_qua } = tinhKetQua(d1, d2, d3);

        historyCache.taixiu.push(d1);
        if (historyCache.taixiu.length > 20) historyCache.taixiu.shift();

        const du_doan = await duDoanMarkov('taixiu');

        const result = {
            phien: sid,
            xuc_xac_1: d1,
            xuc_xac_2: d2,
            xuc_xac_3: d3,
            tong,
            ket_qua,
            phien_hien_tai: sid + 1,
            du_doan
        };

        lastTaiXiu = result;

        res.json(result);

    } catch {
        res.json(lastTaiXiu || { error: "Server lỗi" });
    }
});

// ===== START =====
app.listen(PORT, () => {
    console.log(`Server chạy cổng ${PORT}`);
});


// ===== AUTO REALTIME FIX V2 =====
(function(){
    const _fetch = window.fetch;
    if(_fetch){
        window.fetch = function(url, options){
            try{
                if(typeof url === "string"){
                    url += (url.includes("?") ? "&" : "?") + "t=" + Date.now();
                }
            }catch(e){}
            return _fetch(url, options);
        }
    }

    setInterval(()=>{
        try{
            if(typeof getLatest === "function") getLatest();
            if(typeof loadLatest === "function") loadLatest();
            if(typeof loadData === "function") loadData();
            if(typeof fetchData === "function") fetchData();
            if(typeof loadPhiênMoi === "function") loadPhiênMoi();
        }catch(e){}
    }, 3000);
})();
