const axios = require("axios");

// Danh sách API
const API_LIST = [
    "https://haywin-s1fi.onrender.com/taixiu",
    "https://haywin-s1fi.onrender.com/taixiumd5",
    "https://laucua79-p7tw.onrender.com/taixiu",
    "https://laucua79-p7tw.onrender.com/taixiumd5",
    "https://hitclub-foua.onrender.com/taixiu",
    "https://hitclub-foua.onrender.com/taixiumd5",
    "https://hitclub-foua.onrender.com/sicbo",
    "https://betvip-b8gk.onrender.com/taixiu",
    "https://betvip-b8gk.onrender.com/taixiumd5",
    "https://b52-b74u.onrender.com/taixiu",
    "https://b52-b74u.onrender.com/sicbo",
    "https://b52-b74u.onrender.com/taixiumd5",
    "https://sunwinsicbo-2r4h.onrender.com/sicbo",
    "https://luckywin-9jtl.onrender.com/taixiu",
    "https://luckywin-9jtl.onrender.com/taixiu3phut",
    "https://luckywin-9jtl.onrender.com/taixiumd5",
    "https://bacaratsexy-dmx4.onrender.com/all",
    "https://sao789-kssb.onrender.com/taixiu",
    "https://sao789-kssb.onrender.com/taixiumd5",
    "https://xocdia88-b7dn.onrender.com/taixiu",
    "https://xocdia88-b7dn.onrender.com/taixiumd5",
];

// Header giả lập
const HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
};

// Timeout & interval
const TIMEOUT = 15000;
const SLEEP_INTERVAL = 300000; // 5 phút

// Format thời gian
function now() {
    return new Date().toISOString().replace("T", " ").substring(0, 19);
}

// Ping 1 API
async function pingApi(url) {
    try {
        const res = await axios.get(url, {
            headers: HEADERS,
            timeout: TIMEOUT,
        });

        if (res.status === 200) {
            console.log(`${now()} - ✅ [${url}] OK - ${res.status}`);
        } else {
            console.log(`${now()} - ⚠️ [${url}] Status: ${res.status}`);
        }
    } catch (err) {
        if (err.code === "ECONNABORTED") {
            console.log(`${now()} - ⏱️ [${url}] TIMEOUT`);
        } else if (err.code === "ECONNREFUSED") {
            console.log(`${now()} - 🔌 [${url}] Connection Error`);
        } else {
            console.log(`${now()} - ❌ [${url}] ${err.message}`);
        }
    }
}

// Ping tất cả API (song song)
async function pingAllApis() {
    console.log(`\n=== Bắt đầu quét ${API_LIST.length} API ===`);

    await Promise.all(API_LIST.map(url => pingApi(url)));

    console.log("=== Hoàn thành quét ===\n");
}

// Main loop
async function main() {
    console.log("🚀 Bắt đầu treo API");
    console.log(`📋 Tổng API: ${API_LIST.length}`);
    console.log(`⏰ Chu kỳ: ${SLEEP_INTERVAL / 1000}s\n`);

    while (true) {
        await pingAllApis();

        const next = new Date(Date.now() + SLEEP_INTERVAL);
        console.log(`💤 Đợi đến ${next.toLocaleTimeString()}...\n`);

        await new Promise(resolve => setTimeout(resolve, SLEEP_INTERVAL));
    }
}

main();