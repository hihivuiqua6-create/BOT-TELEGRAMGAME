const WebSocket = require('ws');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
const PORT = process.env.PORT || 2000;

// ================== DỮ LIỆU 2 BÀN ==================
let txData = {      // Bàn Tài Xỉu - SV1
    phien: null,
    xuc_xac_1: null,
    xuc_xac_2: null,
    xuc_xac_3: null,
    tong: null,
    ket_qua: "",
    md5: "",
    id: "@tiendataox",
    timestamp: null
};

let md5Data = {     // Bàn MD5 / Hũ - SV2
    phien: null,
    xuc_xac_1: null,
    xuc_xac_2: null,
    xuc_xac_3: null,
    tong: null,
    ket_qua: "",
    md5: "",
    id: "@tiendataox",
    timestamp: null
};

// ================== CONFIG 2 SERVER ==================
const SERVERS = [
    {
        name: "SV1",
        base: "https://taixiu.apisum.pro",
        hub: "luckydiceHub",
        tid: 1,
        target: txData
    },
    {
        name: "SV2",
        base: "https://taixiu1.apisum.pro",
        hub: "luckydice1Hub",
        tid: 2,
        target: md5Data
    }
];

const HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://play.sum.vin"
};

// ================== LẤY TOKEN & BUILD URL ==================
async function getConnectionToken(server) {
    try {
        const url = `${server.base}/signalr/negotiate?clientProtocol=1.5`;
        const res = await fetch(url, { headers: HEADERS });
        const data = await res.json();
        return data.ConnectionToken;
    } catch (e) {
        console.error(`[${server.name}] Lỗi lấy token`);
        return null;
    }
}

async function buildWsUrl(server) {
    const token = await getConnectionToken(server);
    if (!token) return null;

    const connectionData = encodeURIComponent(JSON.stringify([{ name: server.hub }]));

    return `${server.base.replace('https', 'wss')}/signalr/connect?` +
           `transport=webSockets` +
           `&connectionToken=${encodeURIComponent(token)}` +
           `&connectionData=${connectionData}` +
           `&clientProtocol=1.5` +
           `&tid=${server.tid}`;
}

// ================== XỬ LÝ MESSAGE ==================
function processMessage(serverName, targetData, message) {
    try {
        const data = JSON.parse(message.toString());
        const messages = Array.isArray(data) ? data : (data.M || []);

        for (let m of messages) {
            if (m.M === "sessionInfo" && m.A && m.A[0]) {
                const info = m.A[0];
                const result = info.Result || {};

                if (result.Dice1 > 0 && result.Dice2 > 0 && result.Dice3 > 0) {
                    const tong = result.Dice1 + result.Dice2 + result.Dice3;

                    targetData.phien = info.SessionID || null;
                    targetData.xuc_xac_1 = result.Dice1;
                    targetData.xuc_xac_2 = result.Dice2;
                    targetData.xuc_xac_3 = result.Dice3;
                    targetData.tong = tong;
                    targetData.ket_qua = tong >= 11 ? "Tài" : "Xỉu";
                    targetData.md5 = info.MD5 || "";
                    targetData.timestamp = Date.now();

                    console.log(`[${serverName}] Phiên ${targetData.phien} | ${targetData.xuc_xac_1}-${targetData.xuc_xac_2}-${targetData.xuc_xac_3} | ${tong} (${targetData.ket_qua})`);
                }
            }
        }
    } catch (e) {}
}

// ================== TẠO KẾT NỐI ==================
async function startWebSocket(server) {
    const wsUrl = await buildWsUrl(server);
    if (!wsUrl) return;

    let ws = new WebSocket(wsUrl, { headers: HEADERS });

    ws.on('open', () => {
        console.log(`[✅] ${server.name} Connected`);
        ws.send(JSON.stringify([1, "MiniGame", "GM_apivopnha", "tiendat", {"info":"{}", "signature":""}]));
        ws.send(JSON.stringify([6, "MiniGame", "taixiuPlugin", { cmd: 1005 }]));
    });

    ws.on('message', (msg) => {
        processMessage(server.name, server.target, msg.toString());
    });

    ws.on('close', () => {
        console.log(`[${server.name}] Closed → Reconnect...`);
        setTimeout(() => startWebSocket(server), 3000);
    });

    ws.on('error', () => {});
}

// ================== API ==================
app.get('/api/tx', (req, res) => res.json(txData));     // Bàn Tài Xỉu
app.get('/api/md5', (req, res) => res.json(md5Data));   // Bàn MD5

app.get('/', (req, res) => {
    res.json({
        status: "running",
        tx: "/api/tx",
        md5: "/api/md5"
    });
});

app.listen(PORT, () => {
    console.log(`[🌐] Server chạy tại http://localhost:${PORT}`);
    console.log(`   → /api/tx  : Tài Xỉu`);
    console.log(`   → /api/md5 : MD5 / Hũ\n`);

    // Khởi tạo 2 kết nối
    SERVERS.forEach(server => startWebSocket(server));
});