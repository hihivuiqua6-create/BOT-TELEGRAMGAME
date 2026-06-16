const ai = require('../ai_engine');
const axios = require('axios');
const express = require('express');
const https = require('https');

// ======================
// CẤU HÌNH TÀI KHOẢN (SỬA THEO Ý MÀY)
// ======================
const USERNAME = "6tyghujkm";    // hoặc "tiendatoce1232"
const PASSWORD = "6tyghujkm";    // hoặc "tiendatoceee1"

const BASE = "https://aibcr.me";
const LOGIN_URL = `${BASE}/login`;
const LOBBY_URL = `${BASE}/ae/lobby`;
const GET_RESULT_URL = `${BASE}/baccarat/getnewresult`;

const agent = new https.Agent({ rejectUnauthorized: false });
let cookieJar = '';
let baccaratData = [];
let lastUpdate = null;

// ======================
// SESSION AXIOS (tự động lưu cookie)
// ======================
const session = axios.create({
    baseURL: BASE,
    timeout: 30000,
    httpsAgent: agent,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
    }
});

// Interceptor lưu cookie
session.interceptors.request.use(config => {
    if (cookieJar) config.headers.Cookie = cookieJar;
    return config;
});

session.interceptors.response.use(res => {
    const setCookie = res.headers['set-cookie'];
    if (setCookie) {
        for (const cookie of setCookie) {
            const [name, value] = cookie.split(';')[0].split('=');
            // Xóa cookie cũ nếu có
            const regex = new RegExp(`${name}=[^;]+;?`, 'g');
            cookieJar = cookieJar.replace(regex, '');
            cookieJar += `${name}=${value}; `;
        }
    }
    return res;
});

// ======================
// HÀM LẤY CSRF TOKEN (từ input hidden _token hoặc meta)
// ======================
function getCsrfToken(html) {
    // Ưu tiên tìm trong input hidden name="_token"
    let match = html.match(/<input[^>]*name="_token"[^>]*value="([^"]+)"/);
    if (match) return match[1];
    // Dự phòng tìm trong meta
    match = html.match(/<meta\s+name="csrf-token"\s+content="([^"]+)"/);
    return match ? match[1] : null;
}

// ======================
// ĐĂNG NHẬP (cải tiến)
// ======================
async function login() {
    try {
        console.log('[LOGIN] Đang lấy trang đăng nhập...');
        const getResp = await session.get(LOGIN_URL);
        const token = getCsrfToken(getResp.data);
        if (!token) {
            console.error('[LOGIN] Không tìm thấy CSRF token!');
            return false;
        }
        console.log(`[LOGIN] CSRF token: ${token}`);

        const formData = new URLSearchParams();
        formData.append('username', USERNAME);
        formData.append('password', PASSWORD);
        formData.append('_token', token);
        formData.append('action', 'Login');

        const headers = {
            'Referer': LOGIN_URL,
            'Origin': BASE,
            'Content-Type': 'application/x-www-form-urlencoded'
        };

        console.log('[LOGIN] Đang gửi request đăng nhập...');
        const loginResp = await session.post(LOGIN_URL, formData.toString(), { headers });
        
        // Kiểm tra đăng nhập thành công (thường redirect về dashboard)
        if (loginResp.status === 200 || loginResp.status === 302) {
            console.log('[LOGIN] Thành công!');
            return true;
        }
        console.error(`[LOGIN] Thất bại, status: ${loginResp.status}`);
        return false;
    } catch (error) {
        console.error('[LOGIN] Lỗi:', error.message);
        return false;
    }
}

// ======================
// VÀO LOBBY (cần để set session)
// ======================
async function goToLobby() {
    try {
        console.log('[LOBBY] Đang vào lobby...');
        await session.get(LOBBY_URL);
        console.log('[LOBBY] OK');
        return true;
    } catch (error) {
        console.error('[LOBBY] Lỗi:', error.message);
        return false;
    }
}

// ======================
// LẤY DỮ LIỆU BACCARAT (chuẩn JSON)
// ======================
async function fetchBaccaratData() {
    try {
        // Lấy XSRF token từ cookie (nếu có)
        let xsrfToken = '';
        const xsrfMatch = cookieJar.match(/XSRF-TOKEN=([^;]+)/);
        if (xsrfMatch) xsrfToken = decodeURIComponent(xsrfMatch[1]);
        
        const headers = {
            'Referer': LOBBY_URL,
            'Origin': BASE,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        };
        if (xsrfToken) headers['X-XSRF-TOKEN'] = xsrfToken;

        const formData = new URLSearchParams();
        formData.append('gameCode', 'ae');

        const resp = await session.post(GET_RESULT_URL, formData.toString(), { headers });
        
        if (resp.data && resp.data.code === 200 && Array.isArray(resp.data.data)) {
            // Parse đúng cấu trúc JSON mẫu
            baccaratData = resp.data.data.map(item => ({
                table: item.table_name,          // Tên bàn: "1", "C01", ...
                table_id: item.table_id,
                result: item.result,             // Chuỗi kết quả: "PBPB", ...
                goodRoad: item.goodRoad || '',   // Cầu (nếu có)
                cards: item.cards || '',
                game_code: item.game_code
            }));
            lastUpdate = new Date().toISOString();
            console.log(`[FETCH] Lấy thành công ${baccaratData.length} bàn lúc ${lastUpdate}`);
        } else {
            console.warn('[FETCH] Dữ liệu không đúng format:', resp.data);
        }
        return baccaratData;
    } catch (error) {
        console.error('[FETCH] Lỗi:', error.message);
        return [];
    }
}

// ======================
// VÒNG LẶP CẬP NHẬT TỰ ĐỘNG (mỗi 2 giây)
// ======================
async function autoUpdate() {
    while (true) {
        await fetchBaccaratData();
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

// ======================
// API SERVER (Express)
// ======================
const app = express();
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', '*');
    next();
});

// Lấy tất cả bàn
app.get('/api/baccarat', (req, res) => {
    res.json({
        success: true,
        data: baccaratData,
        lastUpdate: lastUpdate,
        total: baccaratData.length
    });
});

// Lấy theo tên bàn (vd: /api/baccarat/1 hoặc /api/baccarat/C01)
app.get('/api/baccarat/:table', (req, res) => {
    const tableName = req.params.table;
    const found = baccaratData.find(item => item.table === tableName);
    if (found) res.json({ success: true, data: found });
    else res.json({ success: false, message: `Không tìm thấy bàn ${tableName}` });
});

// Lấy 10 kết quả mới nhất (sắp xếp theo số bàn)
app.get('/api/latest', (req, res) => {
    const latest = [...baccaratData].sort((a, b) => {
        const numA = parseInt(a.table) || 0;
        const numB = parseInt(b.table) || 0;
        return numB - numA;
    });
    res.json({ success: true, data: latest.slice(0, 10), lastUpdate: lastUpdate });
});

// ======================
// KHỞI ĐỘNG
// ======================
async function start() {
    console.log('========================================');
    console.log('BACCARAT API SERVER - FIXED VERSION');
    console.log(`Tài khoản: ${USERNAME}`);
    console.log('========================================');

    console.log('[1] Đăng nhập...');
    const loginOk = await login();
    if (!loginOk) {
        console.error('[ERROR] Đăng nhập thất bại! Kiểm tra lại tài khoản hoặc captcha.');
        process.exit(1);
    }

    console.log('[2] Vào lobby...');
    await goToLobby();

    console.log('[3] Lấy dữ liệu lần đầu...');
    await fetchBaccaratData();
    if (baccaratData.length === 0) {
        console.warn('[CẢNH BÁO] Không lấy được bàn nào, có thể API yêu cầu thêm token hoặc session đã hết hạn.');
    } else {
        console.log(`\n📊 DANH SÁCH BÀN HIỆN TẠI:`);
        baccaratData.forEach(item => {
            const resultShort = (item.result || '').substring(0, 20) + (item.result?.length > 20 ? '...' : '');
            console.log(`   ${item.table.padEnd(5)} : ${resultShort.padEnd(25)} | ${item.goodRoad}`);
        });
    }

    // Chạy auto update ngầm
    autoUpdate();

    const PORT = 5000;
    app.listen(PORT, '0.0.0.0', () => {
        console.log(`\n🚀 API SERVER ĐANG CHẠY:`);
        console.log(`   http://localhost:${PORT}/api/baccarat`);
        console.log(`   http://localhost:${PORT}/api/baccarat/1`);
        console.log(`   http://localhost:${PORT}/api/baccarat/C01`);
        console.log(`   http://localhost:${PORT}/api/latest`);
        console.log(`\n⏰ Auto update mỗi 2 giây.`);
    });
}

start();


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
