const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const config = {
  TOKEN: '8694864181:AAH2c7JJsXPqSxj1rsaOP1_OrfVzwDsdK9U',
  ADMIN_ID: 8579975246,
  KEY_PRICES: {
    '1day': 35000,
    '3day': 50000,
    '7day': 75000,
    '30day': 125000,
    'forever': 170000
  },
  BANK_NAME: 'VIETQR Pay',
  BANK_ACCOUNT: 'NGUYEN VAN DAP',
  BANK_NUMBER: '329185405',
  QR_CODE_URL: 'https://i.postimg.cc/ZRT7kDKG/1775410789318.png',
  // API GAME
  SUNWIN_API: 'http://160.250.136.225:3001/prediction',
  SICBO_SUNWIN_API: 'http://160.250.136.225:3000/api/sicbo/sunwin',
  SIC789_API: 'http://160.250.136.225:3002/api/sicbo/789',
  GAME789_API: 'http://160.250.136.225:5003/789',
  BETVIP_TX_API: 'http://160.250.136.225:5001/api/betvip_tx?key=1',
  BETVIP_MD5_API: 'http://160.250.136.225:5001/api/betvip_md5?key=1',
  LC79_TX_API: 'http://160.250.136.225:5001/api/lc79_tx?key=1',
  LC79_MD5_API: 'http://160.250.136.225:5001/api/lc79_md5?key=1',
  XOCDIA88_TX_API: 'http://160.250.136.225:5001/api/xocdia88_tx?key=1',
  XOCDIA88_MD5_API: 'http://160.250.136.225:5001/api/xocdia88_md5?key=1',
  XENGIVE_TX_API: 'http://160.250.136.225:5001/api/xenglive_tx?key=1',
  XENGIVE_MD5_API: 'http://160.250.136.225:5001/api/xenglive_md5?key=1',
  B52_MD5_API: 'http://160.250.136.225:5004/b52',
  HITCLUB_TX_API: 'http://160.250.136.225:5002/hu',
  HITCLUB_MD5_API: 'http://160.250.136.225:5002/md5',
  LUCK8_TX_API: 'http://160.250.136.225:5001/api/luck8_tx?key=1',
  LUCK8_MD5_API: 'http://160.250.136.225:5001/api/luck8_md5?key=1',
  HAYWIN_TX_API: 'http://160.250.136.225:5001/api/haywin_tx?key=1',
  HAYWIN_MD5_API: 'http://160.250.136.225:5001/api/haywin_md5?key=1',
  SON789_TX_API: 'http://160.250.136.225:5001/api/son789_tx?key=1',
  SON789_MD5_API: 'http://160.250.136.225:5001/api/son789_md5?key=1',
  HOT789_TX_API: 'http://160.250.136.225:5001/api/hot789_tx?key=1',
  HOT789_MD5_API: 'http://160.250.136.225:5001/api/hot789_md5?key=1',
  DB_FILE: path.join(__dirname, 'database.json'),
  UPDATE_INTERVAL: 3000
};

const bot = new TelegramBot(config.TOKEN, { polling: true });

let database = { 
    keys: [], 
    users: {}, 
    pendingDeposits: {},
    pendingAddMoney: {},
    pendingSubMoney: {},
    pendingCardDeposit: {},
    pendingBankDeposit: {},
    pendingBroadcast: {},
    userSettings: {},
    maintenance: {
      sunwin: false, sicbo_sunwin: false, sic789: false, game789: false,
      betvip_tx: false, betvip_md5: false, lc79_tx: false, lc79_md5: false,
      xocdia88_tx: false, xocdia88_md5: false, xenglive_tx: false, xenglive_md5: false,
      b52_md5: false, hitclub_tx: false, hitclub_md5: false,
      luck8_tx: false, luck8_md5: false, haywin_tx: false, haywin_md5: false,
      son789_tx: false, son789_md5: false, hot789_tx: false, hot789_md5: false
    }
};

function loadDB() { 
    if (fs.existsSync(config.DB_FILE)) { 
        try { 
            const loaded = JSON.parse(fs.readFileSync(config.DB_FILE, 'utf8'));
            Object.assign(database, loaded);
        } catch (e) {} 
    } 
}
function saveDB() { 
    fs.writeFileSync(config.DB_FILE, JSON.stringify(database, null, 2)); 
}
loadDB();

let activeGames = new Map();
let autoPredictIntervals = new Map();
let lastPhienMap = new Map();

function cleanPhien(val) {
    if (!val) return 0;
    return parseInt(val.toString().replace(/[^0-9]/g, '')) || 0;
}

function checkKey(chatId) {
    if (Number(chatId) === config.ADMIN_ID) return true;
    const user = database.users[chatId];
    if (!user || !user.expiry) return false;
    if (user.expiry === 'forever') return true;
    if (Date.now() > user.expiry) {
        user.expiry = null;
        saveDB();
        return false;
    }
    return true;
}

function getRemainingTime(chatId) {
    const user = database.users[chatId];
    if (!user || !user.expiry) return "❌ Chưa có key";
    if (user.expiry === 'forever') return "👑 VĨNH VIỄN";
    const remaining = user.expiry - Date.now();
    if (remaining <= 0) return "❌ Đã hết hạn";
    const days = Math.floor(remaining / (24 * 60 * 60 * 1000));
    const hours = Math.floor((remaining % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
    const minutes = Math.floor((remaining % (60 * 60 * 1000)) / (60 * 1000));
    return `⏰ ${days} ngày ${hours} giờ ${minutes} phút`;
}

function generateRandomKey(type) {
    const prefix = type === 'forever' ? 'VIP-FOREVER' : 'VIP';
    const randomStr = Math.random().toString(36).substring(2, 2 + 10).toUpperCase();
    const numbers = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
    return `${prefix}-${randomStr}-${numbers}`;
}

function generateRandomContent(userId) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let randomStr = '';
    for (let i = 0; i < 6; i++) {
        randomStr += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return randomStr;
}

function getUserInfo(chatId, username, firstName, lastName) {
    const hasKey = checkKey(chatId);
    const remainingTime = getRemainingTime(chatId);
    const user = database.users[chatId];
    const balance = user?.balance || 0;
    const autoPredict = database.userSettings[chatId]?.autoPredict || false;
    
    let status = "";
    if (Number(chatId) === config.ADMIN_ID) {
        status = "👑 ADMIN";
    } else if (hasKey) {
        status = "✅ ĐÃ KÍCH HOẠT";
    } else {
        status = "❌ CHƯA CÓ KEY";
    }
    
    return {
        status: status,
        hasKey: hasKey,
        remainingTime: remainingTime,
        balance: balance,
        autoPredict: autoPredict,
        username: username || "Chưa có username",
        fullName: `${firstName || ""} ${lastName || ""}`.trim() || "Chưa có tên"
    };
}

async function sendWelcomeMessage(chatId, username, firstName, lastName) {
    const userInfo = getUserInfo(chatId, username, firstName, lastName);
    
    const welcomeText = `🎲 𝐂𝐇𝐀̀𝐎 𝐌𝐔̛̀𝐍𝐆 Đ𝐄̂́𝐍 𝐕𝐎̛́𝐈 𝐇𝐄̣̂ 𝐓𝐇𝐎̂́𝐍𝐆 𝐇𝐎̂̃ 𝐓𝐑𝐎̛̣ 𝐃𝐔̛̣ Đ𝐎𝐀́𝐍 𝐓𝐀̀𝐈 𝐗𝐈̉𝐔 🎲
╔════════════════════════════════════╗
║  👤 𝐓𝐇𝐎̂𝐍𝐆 𝐓𝐈𝐍 𝐍𝐆𝐔̛𝐎̛̀𝐈 𝐃𝐔̀𝐍𝐆
╠════════════════════════════════════╣
║  • 𝐈𝐃: ${chatId}
║  • 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦: @${userInfo.username}
║  • 𝐓𝐞̂𝐧: ${userInfo.fullName}
╠════════════════════════════════════╣
║  💰 𝐒𝐎̂́ 𝐃𝐔̛: ${userInfo.balance.toLocaleString()} VNĐ
╠════════════════════════════════════╣
║  🔐 𝐓𝐑𝐀̣𝐍𝐆 𝐓𝐇𝐀́𝐈 𝐊𝐄𝐘
╠════════════════════════════════════╣
║  • 𝐓𝐢̀𝐧𝐡 𝐭𝐫𝐚̣𝐧𝐠: ${userInfo.status}
║  • 𝐓𝐡𝐨̛̀𝐢 𝐠𝐢𝐚𝐧: ${userInfo.remainingTime}
╚════════════════════════════════════╝

💡 𝐇𝐃𝐒𝐃: 
• 🛒 Mua key để nhận mã kích hoạt
• 🔑 Nhập key để kích hoạt tài khoản
• ⚙️ Cài đặt auto dự đoán

${!userInfo.hasKey && Number(chatId) !== config.ADMIN_ID ? '⚠️ BẠN CẦN MUA VÀ NHẬP KEY ĐỂ SỬ DỤNG DỊCH VỤ!' : '✅ CHÚC BẠN MAY MẮN!'}`;

    return bot.sendMessage(chatId, welcomeText, getMainMenu(chatId));
}

function getMainMenu(chatId) {
    let kb = [
        [{ text: '🎮 CHƠI GAME' }],
        [{ text: '💰 NẠP TIỀN' }, { text: '🛒 MUA KEY' }],
        [{ text: '🔑 NHẬP KEY' }, { text: '⚙️ CÀI ĐẶT' }],
        [{ text: '👤 THÔNG TIN' }, { text: '📞 HỖ TRỢ' }]
    ];
    if (Number(chatId) === config.ADMIN_ID) kb.push([{ text: '⚙️ ADMIN PANEL' }]);
    return { reply_markup: { keyboard: kb, resize_keyboard: true } };
}

function getGameControlMenu() {
    return {
        reply_markup: {
            keyboard: [
                [{ text: '⏹️ DỪNG DỰ ĐOÁN' }],
                [{ text: '🔙 QUAY LẠI MENU GAME' }]
            ],
            resize_keyboard: true
        }
    };
}

async function callAPI(gameType) {
    const apis = {
        'sunwin': { url: config.SUNWIN_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.Prediction, doTinCay: d["Độ Tin Cậy"] }) },
        'sicbo_sunwin': { url: config.SICBO_SUNWIN_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, duDoanVi: d.du_doan_vi, doTinCay: d.do_tin_cay }) },
        'sic789': { url: config.SIC789_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, duDoanVi: d.du_doan_vi, doTinCay: d.do_tin_cay }) },
        'game789': { url: config.GAME789_API, parser: (d) => ({ phien: d.phien, duDoan: d.du_doan, doTinCay: d.ti_le }) },
        'betvip_tx': { url: config.BETVIP_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'betvip_md5': { url: config.BETVIP_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'lc79_tx': { url: config.LC79_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'lc79_md5': { url: config.LC79_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'xocdia88_tx': { url: config.XOCDIA88_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'xocdia88_md5': { url: config.XOCDIA88_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'xenglive_tx': { url: config.XENGIVE_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'xenglive_md5': { url: config.XENGIVE_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'b52_md5': { url: config.B52_MD5_API, parser: (d) => ({ phien: d.phien, duDoan: d.du_doan, doTinCay: d.ti_le }) },
        'hitclub_tx': { url: config.HITCLUB_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'hitclub_md5': { url: config.HITCLUB_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'luck8_tx': { url: config.LUCK8_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'luck8_md5': { url: config.LUCK8_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'haywin_tx': { url: config.HAYWIN_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'haywin_md5': { url: config.HAYWIN_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'son789_tx': { url: config.SON789_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'son789_md5': { url: config.SON789_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'hot789_tx': { url: config.HOT789_TX_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) },
        'hot789_md5': { url: config.HOT789_MD5_API, parser: (d) => ({ phien: d.phien_hien_tai, duDoan: d.du_doan, doTinCay: d.do_tin_cay }) }
    };
    
    const api = apis[gameType];
    if (!api) return null;
    
    try {
        const res = await axios.get(api.url, { timeout: 5000 });
        return api.parser(res.data);
    } catch (e) {
        console.log(`API Error ${gameType}:`, e.message);
        return null;
    }
}

async function updateGamePrediction(chatId, type, isNew = false) {
    const gameNames = {
        'sunwin': '🌸 SUNWIN',
        'sicbo_sunwin': '🎲 SICBO SUNWIN',
        'sic789': '🎲 SIC789',
        'game789': '🎲 GAME789',
        'betvip_tx': '⚡ BETVIP TX',
        'betvip_md5': '⚡ BETVIP MD5',
        'lc79_tx': '👑 LC79 TX',
        'lc79_md5': '🔥 LC79 MD5',
        'xocdia88_tx': '🎯 XOCDIA88 TX',
        'xocdia88_md5': '🎯 XOCDIA88 MD5',
        'xenglive_tx': '🐉 XENG LIVE TX',
        'xenglive_md5': '🐉 XENG LIVE MD5',
        'b52_md5': '💣 B52 MD5',
        'hitclub_tx': '🔥 HITCLUB TX',
        'hitclub_md5': '💎 HITCLUB MD5',
        'luck8_tx': '🍀 LUCK8 TX',
        'luck8_md5': '🍀 LUCK8 MD5',
        'haywin_tx': '⭐ HAYWIN TX',
        'haywin_md5': '⭐ HAYWIN MD5',
        'son789_tx': '🎰 SON789 TX',
        'son789_md5': '🎰 SON789 MD5',
        'hot789_tx': '🔥 HOT789 TX',
        'hot789_md5': '🔥 HOT789 MD5'
    };
    
    const data = await callAPI(type);
    if (!data) {
        await bot.sendMessage(chatId, `⚠️ 𝐋𝐎̂̃𝐈 𝐊𝐄̂́𝐓 𝐍𝐎̂́𝐈 𝐀𝐏𝐈\n🎮 ${gameNames[type] || type.toUpperCase()}\n────────────────────\nVui lòng thử lại sau!`);
        return false;
    }
    
    const currentPhien = data.phien;
    const lastPhien = lastPhienMap.get(`${chatId}_${type}`) || 0;
    
    if (currentPhien !== lastPhien || isNew) {
        lastPhienMap.set(`${chatId}_${type}`, currentPhien);
        
        let text = `🎲 𝐃𝐔̛̣ Đ𝐎𝐀́𝐍 𝐓𝐀̀𝐈 𝐗𝐈̉𝐔 🎲
╔════════════════════════════════════╗
║  🎮 GAME: ${gameNames[type] || type.toUpperCase()}
║  💎 PHIÊN HIỆN TẠI: #${currentPhien}
║  🎯 DỰ ĐOÁN: 【 ${data.duDoan?.toUpperCase() || 'CHỜ...'} 】
`;
        if (data.duDoanVi) {
            text += `║  ✨ VỊ: [ ${data.duDoanVi} ]\n`;
        }
        if (data.doTinCay) {
            text += `║  🔥 ĐỘ TIN CẬY: ${data.doTinCay}\n`;
        }
        text += `╚════════════════════════════════════╝
⏰ ${new Date().toLocaleTimeString('vi-VN')}`;
        
        const sent = await bot.sendMessage(chatId, text);
        return true;
    }
    return false;
}

setInterval(() => {
    const now = Date.now();
    for (const [userId, user] of Object.entries(database.users)) {
        if (user.expiry && user.expiry !== 'forever' && user.expiry < now) {
            user.expiry = null;
            saveDB();
            bot.sendMessage(userId, `⚠️ 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 ⚠️
╔════════════════════════════════════╗
║  🔐 KEY CỦA BẠN ĐÃ HẾT HẠN!
║  
║  🛒 Vui lòng mua key mới
║  tại mục "🛒 MUA KEY"
║  để tiếp tục sử dụng!
╚════════════════════════════════════╝`);
        }
    }
}, 60000);

bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    if (!text) return;

    if (text === '/start') {
        if (autoPredictIntervals.has(chatId)) {
            clearInterval(autoPredictIntervals.get(chatId));
            autoPredictIntervals.delete(chatId);
        }
        activeGames.delete(chatId);
        const username = msg.from.username;
        const firstName = msg.from.first_name;
        const lastName = msg.from.last_name;
        
        if (!database.users[chatId]) {
            database.users[chatId] = { 
                expiry: null,
                balance: 0,
                info: {
                    username: username,
                    firstName: firstName,
                    lastName: lastName,
                    joinedAt: Date.now()
                }
            };
            saveDB();
        }
        if (!database.userSettings[chatId]) {
            database.userSettings[chatId] = { autoPredict: false };
            saveDB();
        }
        
        return sendWelcomeMessage(chatId, username, firstName, lastName);
    }
    
    if (text === '🔙 QUAY LẠI MENU') {
        if (autoPredictIntervals.has(chatId)) {
            clearInterval(autoPredictIntervals.get(chatId));
            autoPredictIntervals.delete(chatId);
        }
        activeGames.delete(chatId);
        return sendWelcomeMessage(chatId, msg.from.username, msg.from.first_name, msg.from.last_name);
    }
    
    if (text === '🔙 QUAY LẠI MENU GAME') {
        if (autoPredictIntervals.has(chatId)) {
            clearInterval(autoPredictIntervals.get(chatId));
            autoPredictIntervals.delete(chatId);
        }
        activeGames.delete(chatId);
        return bot.sendMessage(chatId, "🎮 𝐂𝐡𝐨̣𝐧 𝐠𝐚𝐦𝐞:", { 
            reply_markup: { 
                keyboard: [
                    [{ text: '🎲 TÀI XỈU THƯỜNG' }, { text: '⚡ TÀI XỈU MD5' }],
                    [{ text: '🎰 TÀI XỈU SICBO' }, { text: '🔙 QUAY LẠI MENU' }]
                ], 
                resize_keyboard: true 
            } 
        });
    }
    
    if (text === '⏹️ DỪNG DỰ ĐOÁN') {
        if (autoPredictIntervals.has(chatId)) {
            clearInterval(autoPredictIntervals.get(chatId));
            autoPredictIntervals.delete(chatId);
        }
        activeGames.delete(chatId);
        await bot.sendMessage(chatId, "✅ 𝐃𝐔̛̀𝐍𝐆 𝐃𝐔̛̣ Đ𝐎𝐀́𝐍 𝐓𝐇𝐀̀𝐍𝐇 𝐂𝐎̂𝐍𝐆!", {
            reply_markup: {
                keyboard: [
                    [{ text: '🎲 TÀI XỈU THƯỜNG' }, { text: '⚡ TÀI XỈU MD5' }],
                    [{ text: '🎰 TÀI XỈU SICBO' }, { text: '🔙 QUAY LẠI MENU' }]
                ],
                resize_keyboard: true
            }
        });
        return;
    }
    
    if (text === '👤 THÔNG TIN') {
        return sendWelcomeMessage(chatId, msg.from.username, msg.from.first_name, msg.from.last_name);
    }
    
    if (text === '⚙️ CÀI ĐẶT') {
        const autoStatus = database.userSettings[chatId]?.autoPredict ? "🟢 BẬT" : "🔴 TẮT";
        const settingText = `⚙️ 𝐂𝐀̀𝐈 Đ𝐀̣̆𝐓
╔════════════════════════════════════╗
║  🤖 AUTO DỰ ĐOÁN: ${autoStatus}
╠════════════════════════════════════╣
║  📌 KHI BẬT:
║  • Tự động cập nhật khi
║  • có phiên mới
║  
║  📌 KHI TẮT:
║  • Chỉ gửi dự đoán
║  • 1 lần duy nhất
╚════════════════════════════════════╝`;
        
        return bot.sendMessage(chatId, settingText, {
            reply_markup: {
                inline_keyboard: [
                    [{ text: "🤖 BẬT AUTO DỰ ĐOÁN", callback_data: "auto_on" }],
                    [{ text: "🔴 TẮT AUTO DỰ ĐOÁN", callback_data: "auto_off" }]
                ]
            }
        });
    }
    
    if (text === '🛒 MUA KEY') {
        const priceList = `💎 𝐁𝐀̉𝐍𝐆 𝐆𝐈𝐀́ 𝐊𝐄𝐘 𝐕𝐈𝐏 💎
╔════════════════════════════════════╗
║  📅 1 NGÀY    → 35,000 VNĐ
║  📅 3 NGÀY    → 50,000 VNĐ
║  📅 7 NGÀY    → 75,000 VNĐ
║  📅 30 NGÀY   → 125,000 VNĐ
║  👑 VĨNH VIỄN → 170,000 VNĐ
╚════════════════════════════════════╝

💰 𝐒𝐨̂́ 𝐝𝐮̛ 𝐡𝐢𝐞̣̂𝐧 𝐭𝐚̣𝐢: ${(database.users[chatId]?.balance || 0).toLocaleString()} VNĐ

📌 𝐂𝐚́𝐜𝐡 𝐦𝐮𝐚:
• Chọn gói key phù hợp
• Hệ thống sẽ tự tạo key
• Nhập key để kích hoạt ngay!`;

        return bot.sendMessage(chatId, priceList, {
            reply_markup: {
                inline_keyboard: [
                    [{ text: "📅 MUA KEY 1 NGÀY - 35K", callback_data: "buykey_1day" }],
                    [{ text: "📅 MUA KEY 3 NGÀY - 50K", callback_data: "buykey_3day" }],
                    [{ text: "📅 MUA KEY 7 NGÀY - 75K", callback_data: "buykey_7day" }],
                    [{ text: "📅 MUA KEY 30 NGÀY - 125K", callback_data: "buykey_30day" }],
                    [{ text: "👑 MUA KEY VĨNH VIỄN - 170K", callback_data: "buykey_forever" }],
                    [{ text: "❌ HỦY", callback_data: "buykey_huy" }]
                ]
            }
        });
    }
    
    if (text === '🔑 NHẬP KEY') {
        return bot.sendMessage(chatId, `🔐 𝐍𝐇𝐀̣̂𝐏 𝐊𝐄𝐘 𝐊𝐈́𝐂𝐇 𝐇𝐎𝐀̣𝐓
╔════════════════════════════════════╗
║  📝 Vui lòng gửi mã Key
║  để kích hoạt tài khoản!
║
║  🔑 Key có dạng:
║  VIP-XXXXXXXXXX-XXXX
╚════════════════════════════════════╝`);
    }
    
    if (text === '💰 NẠP TIỀN') {
        return bot.sendMessage(chatId, "💳 𝐂𝐇𝐎̣𝐍 𝐇𝐈̀𝐍𝐇 𝐓𝐇𝐔̛́𝐂 𝐍𝐀̣𝐏 𝐓𝐈𝐄̂̀𝐍:", {
            reply_markup: {
                inline_keyboard: [
                    [{ text: "🏦 CHUYỂN KHOẢN NGÂN HÀNG", callback_data: "nap_chuyenkhoan" }],
                    [{ text: "📱 THẺ CÀO ĐIỆN THOẠI", callback_data: "nap_thecao" }],
                    [{ text: "❌ HỦY", callback_data: "nap_huy" }]
                ]
            }
        });
    }
    
    if (text === '⚙️ ADMIN PANEL' && Number(chatId) === config.ADMIN_ID) {
        return bot.sendMessage(chatId, "🛠 𝐏𝐀𝐍𝐄𝐋 𝐀𝐃𝐌𝐈𝐍", {
            reply_markup: { 
                keyboard: [
                    [{ text: '🎁 TẠO KEY' }, { text: '👥 DANH SÁCH USER' }],
                    [{ text: '➕ CỘNG TIỀN' }, { text: '➖ TRỪ TIỀN' }],
                    [{ text: '🔧 BẢO TRÌ GAME' }, { text: '📋 ĐƠN NẠP CHỜ' }],
                    [{ text: '🔍 DUYỆT ĐƠN' }, { text: '📢 THÔNG BÁO' }],
                    [{ text: '🔙 QUAY LẠI MENU' }]
                ], 
                resize_keyboard: true 
            }
        });
    }
    
    if (text === '📢 THÔNG BÁO' && Number(chatId) === config.ADMIN_ID) {
        database.pendingBroadcast[chatId] = { step: 'waiting_content' };
        saveDB();
        return bot.sendMessage(chatId, `📢 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 𝐓𝐎𝐀̀𝐍 𝐁𝐎̣̂ 𝐍𝐆𝐔̛𝐎̛̀𝐈 𝐃𝐔̀𝐍𝐆
╔════════════════════════════════════╗
║  📝 Vui lòng nhập nội dung
║  thông báo bạn muốn gửi!
╚════════════════════════════════════╝`);
    }
    
    if (database.pendingBroadcast[chatId] && database.pendingBroadcast[chatId].step === 'waiting_content' && Number(chatId) === config.ADMIN_ID) {
        const content = text;
        database.pendingBroadcast[chatId].content = content;
        database.pendingBroadcast[chatId].step = 'waiting_confirm';
        saveDB();
        
        const confirmMsg = `📢 𝐗𝐀́𝐂 𝐍𝐇𝐀̣̂𝐍 𝐆𝐔̛̉𝐈 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎
╔════════════════════════════════════╗
║  📝 NỘI DUNG:
║  ${content}
╠════════════════════════════════════╣
║  👥 Số người sẽ nhận: ${Object.keys(database.users).length}
╚════════════════════════════════════╝

🔧 𝐁𝐀̣𝐍 𝐂𝐎́ 𝐂𝐇𝐀̆́𝐂 𝐂𝐇𝐀̆́𝐍 𝐌𝐔𝐎̂́𝐍 𝐆𝐔̛̉𝐈?`;
        
        return bot.sendMessage(chatId, confirmMsg, {
            reply_markup: {
                inline_keyboard: [
                    [{ text: "✅ GỬI NGAY", callback_data: "broadcast_confirm" }],
                    [{ text: "❌ HỦY", callback_data: "broadcast_cancel" }]
                ]
            }
        });
    }
    
    if (text === '📋 ĐƠN NẠP CHỜ' && Number(chatId) === config.ADMIN_ID) {
        const pendingList = Object.entries(database.pendingDeposits)
            .filter(([id, d]) => d.status === 'pending')
            .map(([id, d]) => {
                return `🆔 ${id}\n👤 USER: ${d.userId}\n👤 NAME: @${d.username || 'không có'}\n💰 ${d.amount?.toLocaleString() || '?'} VNĐ\n📱 ${d.type === 'card' ? 'THẺ CÀO' : 'CHUYỂN KHOẢN'}\n📝 ND: ${d.content || ''}\n⏰ ${new Date(d.time).toLocaleString('vi-VN')}\n────────────────`;
            });
        const textMsg = pendingList.length > 0 ? `📋 𝐃𝐀𝐍𝐇 𝐒𝐀́𝐂𝐇 Đ𝐎̛𝐍 𝐂𝐇𝐎̛̀:\n────────────────\n${pendingList.join('\n')}` : "📋 Không có đơn nào!";
        bot.sendMessage(chatId, textMsg);
        return;
    }
    
    if (text === '🔍 DUYỆT ĐƠN' && Number(chatId) === config.ADMIN_ID) {
        global.waitingOrderSearch = true;
        return bot.sendMessage(chatId, "🔍 𝐓𝐑𝐀 𝐂𝐔̛́𝐔 Đ𝐎̛𝐍 𝐍𝐀̣𝐏\n────────────────────\n📝 Nhập mã đơn cần duyệt:");
    }
    
    if (global.waitingOrderSearch) {
        const depositId = text;
        const deposit = database.pendingDeposits[depositId];
        
        if (!deposit) {
            await bot.sendMessage(chatId, `❌ Không tìm thấy đơn hàng có mã: ${depositId}`);
            delete global.waitingOrderSearch;
            return;
        }
        
        const statusText = deposit.status === 'pending' ? '⏳ CHỜ DUYỆT' : 
                          (deposit.status === 'approved' ? '✅ ĐÃ DUYỆT' : '❌ ĐÃ HỦY');
        
        const infoText = `📋 𝐓𝐇𝐎̂𝐍𝐆 𝐓𝐈𝐍 Đ𝐎̛𝐍 𝐇𝐀̀𝐍𝐆
╔════════════════════════════════════╗
║  🆔 MÃ ĐƠN: ${depositId}
║  👤 USER ID: ${deposit.userId}
║  👤 USERNAME: @${deposit.username || 'không có'}
║  📱 LOẠI: ${deposit.type === 'card' ? 'THẺ CÀO' : 'CHUYỂN KHOẢN'}
║  💰 SỐ TIỀN: ${deposit.amount?.toLocaleString() || '?'} VNĐ
║  📌 TRẠNG THÁI: ${statusText}
║  ⏰ THỜI GIAN: ${new Date(deposit.time).toLocaleString('vi-VN')}
╚════════════════════════════════════╝`;
        
        await bot.sendMessage(chatId, infoText);
        
        if (deposit.status === 'pending') {
            await bot.sendMessage(chatId, "🔧 𝐂𝐇𝐎̣𝐍 𝐇𝐀̀𝐍𝐇 Đ𝐎̣̂𝐍𝐆:", {
                reply_markup: {
                    inline_keyboard: [
                        [{ text: "✅ DUYỆT ĐƠN", callback_data: `duyet_don_${depositId}` }],
                        [{ text: "❌ HỦY ĐƠN", callback_data: `huy_don_admin_${depositId}` }]
                    ]
                }
            });
        }
        
        delete global.waitingOrderSearch;
        return;
    }

    if (text === '🔧 BẢO TRÌ GAME' && Number(chatId) === config.ADMIN_ID) {
        const gameList = getGameListForMaintenance();
        return bot.sendMessage(chatId, "🔧 𝐂𝐇𝐎̣𝐍 𝐆𝐀𝐌𝐄 𝐂𝐀̂̀𝐍 𝐁𝐀̉𝐎 𝐓𝐑𝐈̀:", {
            reply_markup: { inline_keyboard: gameList }
        });
    }

    if (text === '🎁 TẠO KEY' && Number(chatId) === config.ADMIN_ID) {
        return bot.sendMessage(chatId, "𝐂𝐡𝐨̣𝐧 𝐥𝐨𝐚̣𝐢 𝐊𝐞𝐲 𝐜𝐚̂̀𝐧 𝐭𝐚̣𝐨:", {
            reply_markup: { 
                inline_keyboard: [
                    [{ text: "📅 KEY 1 NGÀY", callback_data: "gen_1day" }],
                    [{ text: "📅 KEY 3 NGÀY", callback_data: "gen_3day" }],
                    [{ text: "📅 KEY 7 NGÀY", callback_data: "gen_7day" }],
                    [{ text: "📅 KEY 30 NGÀY", callback_data: "gen_30day" }],
                    [{ text: "👑 KEY VĨNH VIỄN", callback_data: "gen_forever" }]
                ] 
            }
        });
    }
    
    if (text === '➕ CỘNG TIỀN' && Number(chatId) === config.ADMIN_ID) {
        database.pendingAddMoney[chatId] = { step: 'waiting_id' };
        saveDB();
        return bot.sendMessage(chatId, "💸 𝐂𝐎̣̂𝐍𝐆 𝐓𝐈𝐄̂̀𝐍 𝐂𝐇𝐎 𝐔𝐒𝐄𝐑\n────────────────────\n📝 Vui lòng nhập ID Telegram của người dùng:");
    }
    
    if (database.pendingAddMoney[chatId] && database.pendingAddMoney[chatId].step === 'waiting_id' && Number(chatId) === config.ADMIN_ID) {
        const targetId = text;
        const user = database.users[targetId];
        if (user) {
            database.pendingAddMoney[chatId] = { step: 'waiting_amount', targetId: targetId };
            saveDB();
            return bot.sendMessage(chatId, `✅ Đã chọn user: ${targetId} - @${user.info?.username || 'không có username'}\n💰 Nhập số tiền muốn cộng (VD: 50000):`);
        } else {
            return bot.sendMessage(chatId, "❌ Không tìm thấy user với ID này! Vui lòng nhập ID hợp lệ:");
        }
    }
    
    if (database.pendingAddMoney[chatId] && database.pendingAddMoney[chatId].step === 'waiting_amount' && Number(chatId) === config.ADMIN_ID) {
        const amount = parseInt(text);
        const targetId = database.pendingAddMoney[chatId].targetId;
        
        if (!isNaN(amount) && amount > 0) {
            if (!database.users[targetId]) {
                database.users[targetId] = { expiry: null, balance: 0, info: {} };
            }
            
            const oldBalance = database.users[targetId].balance || 0;
            database.users[targetId].balance = oldBalance + amount;
            delete database.pendingAddMoney[chatId];
            saveDB();
            
            await bot.sendMessage(chatId, `✅ Đã cộng ${amount.toLocaleString()} VNĐ thành công cho user ${targetId}\n💰 Số dư mới: ${database.users[targetId].balance.toLocaleString()} VNĐ`);
            await bot.sendMessage(targetId, `🎉 𝐓𝐀̀𝐈 𝐊𝐇𝐎𝐀̉𝐍 𝐂𝐔̉𝐀 𝐁𝐀̣𝐍 𝐕𝐔̛̀𝐀 Đ𝐔̛𝐎̛̣𝐂 𝐀𝐃𝐌𝐈𝐍 𝐂𝐎̣̂𝐍𝐆 𝐓𝐇𝐄̂𝐌 ${amount.toLocaleString()} 𝐕𝐍Đ\n────────────────────\n💰 𝐒𝐨̂́ 𝐝𝐮̛ 𝐡𝐢𝐞̣̂𝐧 𝐭𝐚̣𝐢: ${database.users[targetId].balance.toLocaleString()} VNĐ`);
        } else {
            return bot.sendMessage(chatId, "❌ Số tiền không hợp lệ! Vui lòng nhập số tiền hợp lệ:");
        }
        return;
    }
    
    // TRỪ TIỀN
    if (text === '➖ TRỪ TIỀN' && Number(chatId) === config.ADMIN_ID) {
        database.pendingSubMoney[chatId] = { step: 'waiting_id' };
        saveDB();
        return bot.sendMessage(chatId, "💸 𝐓𝐑𝐔̛̀ 𝐓𝐈𝐄̂̀𝐍 𝐂𝐔̉𝐀 𝐔𝐒𝐄𝐑\n────────────────────\n📝 Vui lòng nhập ID Telegram của người dùng:");
    }
    
    if (database.pendingSubMoney[chatId] && database.pendingSubMoney[chatId].step === 'waiting_id' && Number(chatId) === config.ADMIN_ID) {
        const targetId = text;
        const user = database.users[targetId];
        if (user) {
            database.pendingSubMoney[chatId] = { step: 'waiting_amount', targetId: targetId };
            saveDB();
            return bot.sendMessage(chatId, `✅ Đã chọn user: ${targetId} - @${user.info?.username || 'không có username'}\n💰 Nhập số tiền muốn trừ (VD: 50000):`);
        } else {
            return bot.sendMessage(chatId, "❌ Không tìm thấy user với ID này! Vui lòng nhập ID hợp lệ:");
        }
    }
    
    if (database.pendingSubMoney[chatId] && database.pendingSubMoney[chatId].step === 'waiting_amount' && Number(chatId) === config.ADMIN_ID) {
        const amount = parseInt(text);
        const targetId = database.pendingSubMoney[chatId].targetId;
        
        if (!isNaN(amount) && amount > 0) {
            if (!database.users[targetId]) {
                database.users[targetId] = { expiry: null, balance: 0, info: {} };
            }
            
            const oldBalance = database.users[targetId].balance || 0;
            if (oldBalance >= amount) {
                database.users[targetId].balance = oldBalance - amount;
                delete database.pendingSubMoney[chatId];
                saveDB();
                
                await bot.sendMessage(chatId, `✅ Đã trừ ${amount.toLocaleString()} VNĐ thành công cho user ${targetId}\n💰 Số dư mới: ${database.users[targetId].balance.toLocaleString()} VNĐ`);
                await bot.sendMessage(targetId, `⚠️ 𝐓𝐀̀𝐈 𝐊𝐇𝐎𝐀̉𝐍 𝐂𝐔̉𝐀 𝐁𝐀̣𝐍 𝐕𝐔̛̀𝐀 𝐁𝐈̣ 𝐀𝐃𝐌𝐈𝐍 𝐓𝐑𝐔̛̀ ${amount.toLocaleString()} 𝐕𝐍Đ\n────────────────────\n💰 𝐒𝐨̂́ 𝐝𝐮̛ 𝐡𝐢𝐞̣̂𝐧 𝐭𝐚̣𝐢: ${database.users[targetId].balance.toLocaleString()} VNĐ`);
            } else {
                return bot.sendMessage(chatId, `❌ Số dư của user ${targetId} không đủ! (${oldBalance.toLocaleString()} VNĐ)`);
            }
        } else {
            return bot.sendMessage(chatId, "❌ Số tiền không hợp lệ! Vui lòng nhập số tiền hợp lệ:");
        }
        return;
    }
    
    if (text === '👥 DANH SÁCH USER' && Number(chatId) === config.ADMIN_ID) {
        const userList = Object.entries(database.users)
            .filter(([id, user]) => Number(id) !== config.ADMIN_ID)
            .map(([id, user]) => {
                const hasKey = checkKey(id);
                const expiry = user.expiry === 'forever' ? "Vĩnh viễn" : (user.expiry ? new Date(user.expiry).toLocaleString('vi-VN') : "Chưa có key");
                const balance = user.balance || 0;
                return `🆔 ${id}\n👤 @${user.info?.username || 'không có username'}\n👤 ${user.info?.firstName || ''} ${user.info?.lastName || ''}\n💰 ${balance.toLocaleString()} VNĐ\n🔑 ${hasKey ? "✅ Còn hạn" : "❌ Hết hạn"}\n📅 ${expiry}\n────────────────`;
            });
        
        const userText = userList.length > 0 ? 
            `👥 𝐃𝐀𝐍𝐇 𝐒𝐀́𝐂𝐇 𝐍𝐆𝐔̛𝐎̛̀𝐈 𝐃𝐔̀𝐍𝐆:\n────────────────\n${userList.join('\n')}` : 
            "Chưa có người dùng nào!";
        
        return bot.sendMessage(chatId, userText, getMainMenu(chatId));
    }

    const isMenuText = ['🎮 CHƠI GAME', '💰 NẠP TIỀN', '🛒 MUA KEY', '🔑 NHẬP KEY', '⚙️ CÀI ĐẶT', '📞 HỖ TRỢ', '⚙️ ADMIN PANEL', '🎁 TẠO KEY', '👥 DANH SÁCH USER', '➕ CỘNG TIỀN', '➖ TRỪ TIỀN', '🔧 BẢO TRÌ GAME', '📋 ĐƠN NẠP CHỜ', '🔍 DUYỆT ĐƠN', '📢 THÔNG BÁO', '🎲 TÀI XỈU THƯỜNG', '⚡ TÀI XỈU MD5', '🎰 TÀI XỈU SICBO', '👤 THÔNG TIN', '🔙 QUAY LẠI MENU', '🔙 QUAY LẠI MENU GAME', '⏹️ DỪNG DỰ ĐOÁN'].includes(text);
    
    if (!isMenuText && text !== '/start' && !activeGames.has(chatId) && !database.pendingAddMoney[chatId] && !database.pendingSubMoney[chatId] && !database.pendingCardDeposit[chatId] && !database.pendingBankDeposit[chatId] && text.startsWith('VIP-')) {
        const keyIdx = database.keys.findIndex(k => k.code === text);
        if (keyIdx !== -1) {
            const keyData = database.keys[keyIdx];
            let expiry;
            if (keyData.type === 'forever') {
                expiry = 'forever';
            } else {
                expiry = Date.now() + (keyData.days * 24 * 60 * 60 * 1000);
            }
            
            database.users[chatId] = { 
                ...database.users[chatId],
                expiry: expiry,
                balance: database.users[chatId]?.balance || 0,
                info: {
                    ...database.users[chatId]?.info,
                    username: msg.from.username,
                    firstName: msg.from.first_name,
                    lastName: msg.from.last_name
                }
            };
            database.keys.splice(keyIdx, 1);
            saveDB();
            
            const successMsg = `🎉 𝐊𝐈́𝐂𝐇 𝐇𝐎𝐀̣𝐓 𝐓𝐀̀𝐈 𝐊𝐇𝐎𝐀̉𝐍 𝐓𝐇𝐀̀𝐍𝐇 𝐂𝐎̂𝐍𝐆 🎉
╔════════════════════════════════════╗
║  ✅ KEY: ${text}
║  📅 HẠN: ${keyData.type === 'forever' ? 'VĨNH VIỄN' : keyData.days + ' NGÀY'}
║  👤 USER: ${msg.from.first_name || ''} ${msg.from.last_name || ''}
║  🆔 ID: ${chatId}
╚════════════════════════════════════╝

🎮 𝐂𝐡𝐮́𝐜 𝐛𝐚̣𝐧 𝐜𝐨́ 𝐧𝐡𝐮̛̃𝐧𝐠 𝐭𝐫𝐚̉𝐢 𝐧𝐠𝐡𝐢𝐞̣̂𝐦 𝐭𝐮𝐲𝐞̣̂𝐭 𝐯𝐨̛̀𝐢!`;
            
            await bot.sendMessage(chatId, successMsg);
            return sendWelcomeMessage(chatId, msg.from.username, msg.from.first_name, msg.from.last_name);
        } else {
            const errorMsg = `❌ 𝐊𝐄𝐘 𝐊𝐇𝐎̂𝐍𝐆 𝐇𝐎̛̣𝐏 𝐋𝐄̣̂ 𝐇𝐎𝐀̣̆𝐂 Đ𝐀̃ 𝐇𝐄̂́𝐓 𝐇𝐀̣𝐍 ❌
╔════════════════════════════════════╗
║  🔑 KEY: ${text}
║  ⚠️ Vui lòng kiểm tra lại!
║  🛒 Mua key mới tại mục
║  "🛒 MUA KEY"
╚════════════════════════════════════╝`;
            return bot.sendMessage(chatId, errorMsg);
        }
    }

    if (database.pendingBankDeposit[chatId] && database.pendingBankDeposit[chatId].step === 'waiting_amount') {
        const amount = parseInt(text);
        if (isNaN(amount) || amount <= 0) {
            return bot.sendMessage(chatId, "❌ Số tiền không hợp lệ! Vui lòng nhập số tiền (VD: 100000):");
        }
        
        database.pendingBankDeposit[chatId].amount = amount;
        database.pendingBankDeposit[chatId].step = 'waiting_confirm';
        saveDB();
        
        const randomContent = generateRandomContent(chatId);
        const depositId = Date.now().toString();
        
        database.pendingBankDeposit[chatId].depositId = depositId;
        database.pendingBankDeposit[chatId].content = randomContent;
        saveDB();
        
        const bankInfo = `🏦 𝐓𝐇𝐎̂𝐍𝐆 𝐓𝐈𝐍 𝐂𝐇𝐔𝐘𝐄̂̉𝐍 𝐊𝐇𝐎𝐀̉𝐍
╔════════════════════════════════════╗
║  🏛 NGÂN HÀNG: ${config.BANK_NAME}
║  👤 CHỦ TK: ${config.BANK_ACCOUNT}
║  🔢 SỐ TK: ${config.BANK_NUMBER}
╠════════════════════════════════════╣
║  💰 SỐ TIỀN: ${amount.toLocaleString()} VNĐ
║  📝 NỘI DUNG: ${randomContent}
║  🆔 MÃ ĐƠN: ${depositId}
╚════════════════════════════════════╝

✅ Sau khi chuyển khoản xong, bấm nút bên dưới!`;
        
        await bot.sendPhoto(chatId, config.QR_CODE_URL, {
            caption: bankInfo,
            reply_markup: {
                inline_keyboard: [
                    [{ text: "✅ ĐÃ CHUYỂN KHOẢN", callback_data: `da_chuyen_${depositId}` }],
                    [{ text: "❌ HỦY", callback_data: "nap_huy" }]
                ]
            }
        });
        return;
    }

    if (database.pendingCardDeposit[chatId] && database.pendingCardDeposit[chatId].step === 'waiting_provider') {
        let provider = '';
        if (text === 'VIETTEL') provider = 'VIETTEL';
        else if (text === 'VINAPHONE') provider = 'VINAPHONE';
        else if (text === 'MOBIFONE') provider = 'MOBIFONE';
        else {
            return bot.sendMessage(chatId, "❌ Nhà mạng không hợp lệ! Vui lòng chọn:\nVIETTEL\nVINAPHONE\nMOBIFONE");
        }
        
        database.pendingCardDeposit[chatId].provider = provider;
        database.pendingCardDeposit[chatId].step = 'waiting_amount';
        saveDB();
        return bot.sendMessage(chatId, `✅ Đã chọn nhà mạng: ${provider}\n💰 Nhập mệnh giá thẻ (10000, 20000, 50000, 100000, 200000, 500000):`);
    }
    
    if (database.pendingCardDeposit[chatId] && database.pendingCardDeposit[chatId].step === 'waiting_amount') {
        const amount = parseInt(text);
        const validAmounts = [10000, 20000, 50000, 100000, 200000, 500000];
        
        if (!validAmounts.includes(amount)) {
            return bot.sendMessage(chatId, "❌ Mệnh giá không hợp lệ! Vui lòng chọn: 10000, 20000, 50000, 100000, 200000, 500000");
        }
        
        database.pendingCardDeposit[chatId].amount = amount;
        database.pendingCardDeposit[chatId].step = 'waiting_serial';
        saveDB();
        return bot.sendMessage(chatId, `✅ Mệnh giá: ${amount.toLocaleString()} VNĐ\n📇 Nhập serial thẻ (8-12 số):`);
    }
    
    if (database.pendingCardDeposit[chatId] && database.pendingCardDeposit[chatId].step === 'waiting_serial') {
        const serial = text;
        if (serial.length < 8 || serial.length > 12) {
            return bot.sendMessage(chatId, "❌ Serial không hợp lệ! Vui lòng nhập 8-12 số:");
        }
        
        database.pendingCardDeposit[chatId].serial = serial;
        database.pendingCardDeposit[chatId].step = 'waiting_code';
        saveDB();
        return bot.sendMessage(chatId, `✅ Serial: ${serial}\n🔢 Nhập mã thẻ (12-16 số):`);
    }
    
    if (database.pendingCardDeposit[chatId] && database.pendingCardDeposit[chatId].step === 'waiting_code') {
        const code = text;
        if (code.length < 12 || code.length > 16) {
            return bot.sendMessage(chatId, "❌ Mã thẻ không hợp lệ! Vui lòng nhập 12-16 số:");
        }
        
        const cardInfo = database.pendingCardDeposit[chatId];
        const depositId = Date.now().toString();
        
        database.pendingDeposits[depositId] = {
            userId: chatId,
            type: 'card',
            provider: cardInfo.provider,
            amount: cardInfo.amount,
            serial: cardInfo.serial,
            code: code,
            username: msg.from.username,
            time: Date.now(),
            status: 'pending',
            content: `Thẻ ${cardInfo.provider} ${cardInfo.amount.toLocaleString()}`
        };
        
        delete database.pendingCardDeposit[chatId];
        saveDB();
        
        await bot.sendMessage(chatId, `✅ 𝐃𝐀̃ 𝐆𝐇𝐈 𝐍𝐇𝐀̣̂𝐍 𝐓𝐇𝐄̉ 𝐂𝐀̀𝐎!
╔════════════════════════════════════╗
║  🆔 MÃ ĐƠN: ${depositId}
║  💰 MỆNH GIÁ: ${cardInfo.amount.toLocaleString()} VNĐ
║  ⏰ Vui lòng đợi admin duyệt!
╚════════════════════════════════════╝`);
        
        const adminMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${msg.from.first_name || ''} ${msg.from.last_name || ''}
🌐 Username: @${msg.from.username || 'không có'}
🆔 ID User: ${chatId}

💰 Số tiền nạp: ${cardInfo.amount.toLocaleString()} VNĐ
📱 Hình thức: THẺ CÀO (${cardInfo.provider})
🔑 Mã Giao Dịch: ${depositId}

⏳ TRẠNG THÁI: CHỜ DUYỆT`;
        
        await bot.sendMessage(config.ADMIN_ID, adminMsg, {
            reply_markup: {
                inline_keyboard: [
                    [{ text: "✅ DUYỆT", callback_data: `duyet_card_${depositId}_${cardInfo.amount}` }],
                    [{ text: "❌ HỦY", callback_data: `huy_${depositId}` }]
                ]
            }
        });
        return;
    }

    if (text === '🎮 CHƠI GAME') {
        if (!checkKey(chatId) && Number(chatId) !== config.ADMIN_ID) {
            return bot.sendMessage(chatId, `⚠️ 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 ⚠️
╔════════════════════════════════════╗
║  🔐 Tài khoản chưa được
║     kích hoạt!
║  
║  🛒 Vui lòng mua key và
║     nhập để sử dụng!
║  
║  📌 Vào mục "🛒 MUA KEY"
║     để nhận key ngay!
╚════════════════════════════════════╝`);
        }
        return bot.sendMessage(chatId, "🎮 𝐂𝐡𝐨̣𝐧 𝐠𝐚𝐦𝐞:", { 
            reply_markup: { 
                keyboard: [
                    [{ text: '🎲 TÀI XỈU THƯỜNG' }, { text: '⚡ TÀI XỈU MD5' }],
                    [{ text: '🎰 TÀI XỈU SICBO' }, { text: '🔙 QUAY LẠI MENU' }]
                ], 
                resize_keyboard: true 
            } 
        });
    }

    if (text === '🎲 TÀI XỈU THƯỜNG') {
        if (!checkKey(chatId) && Number(chatId) !== config.ADMIN_ID) {
            return bot.sendMessage(chatId, `⚠️ 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 ⚠️
╔════════════════════════════════════╗
║  🔐 Tài khoản chưa được
║     kích hoạt!
║  
║  🛒 Vui lòng mua key và
║     nhập để sử dụng!
║  
║  📌 Vào mục "🛒 MUA KEY"
║     để nhận key ngay!
╚════════════════════════════════════╝`);
        }
        return bot.sendMessage(chatId, "🎲 𝐂𝐨̂̉𝐧𝐠 𝐓𝐡𝐮̛𝐨̛̀𝐧𝐠:", { 
            reply_markup: { 
                keyboard: [
                    [{ text: '🌸 SUNWIN' }, { text: '💣 B52 MD5' }],
                    [{ text: '👑 LC79 TX' }, { text: '🔥 HITCLUB TX' }],
                    [{ text: '⚡ BETVIP TX' }, { text: '🎯 XOCDIA88 TX' }],
                    [{ text: '🍀 LUCK8 TX' }, { text: '⭐ HAYWIN TX' }],
                    [{ text: '🎰 SON789 TX' }, { text: '🔥 HOT789 TX' }],
                    [{ text: '🐉 XENG LIVE TX' }, { text: '🔙 QUAY LẠI MENU' }]
                ], 
                resize_keyboard: true 
            } 
        });
    }
    
    if (text === '⚡ TÀI XỈU MD5') {
        if (!checkKey(chatId) && Number(chatId) !== config.ADMIN_ID) {
            return bot.sendMessage(chatId, `⚠️ 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 ⚠️
╔════════════════════════════════════╗
║  🔐 Tài khoản chưa được
║     kích hoạt!
║  
║  🛒 Vui lòng mua key và
║     nhập để sử dụng!
║  
║  📌 Vào mục "🛒 MUA KEY"
║     để nhận key ngay!
╚════════════════════════════════════╝`);
        }
        return bot.sendMessage(chatId, "⚡ 𝐂𝐨̂̉𝐧𝐠 𝐌𝐃𝟓:", { 
            reply_markup: { 
                keyboard: [
                    [{ text: '⚡ BETVIP MD5' }, { text: '🔥 LC79 MD5' }],
                    [{ text: '🎯 XOCDIA88 MD5' }, { text: '🐉 XENG LIVE MD5' }],
                    [{ text: '🍀 LUCK8 MD5' }, { text: '⭐ HAYWIN MD5' }],
                    [{ text: '🎰 SON789 MD5' }, { text: '🔥 HOT789 MD5' }],
                    [{ text: '💎 HITCLUB MD5' }, { text: '🔙 QUAY LẠI MENU' }]
                ], 
                resize_keyboard: true 
            } 
        });
    }

    if (text === '🎰 TÀI XỈU SICBO') {
        if (!checkKey(chatId) && Number(chatId) !== config.ADMIN_ID) {
            return bot.sendMessage(chatId, `⚠️ 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 ⚠️
╔════════════════════════════════════╗
║  🔐 Tài khoản chưa được
║     kích hoạt!
║  
║  🛒 Vui lòng mua key và
║     nhập để sử dụng!
║  
║  📌 Vào mục "🛒 MUA KEY"
║     để nhận key ngay!
╚════════════════════════════════════╝`);
        }
        return bot.sendMessage(chatId, "🎰 𝐂𝐨̂̉𝐧𝐠 𝐒𝐈𝐂𝐁𝐎:", { 
            reply_markup: { 
                keyboard: [
                    [{ text: '🎲 SICBO SUNWIN' }, { text: '🎲 SIC789' }],
                    [{ text: '🎲 GAME789' }, { text: '🔙 QUAY LẠI MENU' }]
                ], 
                resize_keyboard: true 
            } 
        });
    }

    const gameMap = { 
        '🌸 SUNWIN': 'sunwin',
        '🎲 SICBO SUNWIN': 'sicbo_sunwin',
        '🎲 SIC789': 'sic789',
        '🎲 GAME789': 'game789',
        '⚡ BETVIP TX': 'betvip_tx',
        '⚡ BETVIP MD5': 'betvip_md5',
        '👑 LC79 TX': 'lc79_tx',
        '🔥 LC79 MD5': 'lc79_md5',
        '🎯 XOCDIA88 TX': 'xocdia88_tx',
        '🎯 XOCDIA88 MD5': 'xocdia88_md5',
        '🐉 XENG LIVE TX': 'xenglive_tx',
        '🐉 XENG LIVE MD5': 'xenglive_md5',
        '💣 B52 MD5': 'b52_md5',
        '🔥 HITCLUB TX': 'hitclub_tx',
        '💎 HITCLUB MD5': 'hitclub_md5',
        '🍀 LUCK8 TX': 'luck8_tx',
        '🍀 LUCK8 MD5': 'luck8_md5',
        '⭐ HAYWIN TX': 'haywin_tx',
        '⭐ HAYWIN MD5': 'haywin_md5',
        '🎰 SON789 TX': 'son789_tx',
        '🎰 SON789 MD5': 'son789_md5',
        '🔥 HOT789 TX': 'hot789_tx',
        '🔥 HOT789 MD5': 'hot789_md5'
    };
    
    if (gameMap[text]) {
        const gameType = gameMap[text];
        
        if (!checkKey(chatId) && Number(chatId) !== config.ADMIN_ID) {
            return bot.sendMessage(chatId, `⚠️ 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 ⚠️
╔════════════════════════════════════╗
║  🔐 Tài khoản chưa được
║     kích hoạt!
║  
║  🛒 Vui lòng mua key và
║     nhập để sử dụng!
║  
║  📌 Vào mục "🛒 MUA KEY"
║     để nhận key ngay!
╚════════════════════════════════════╝`);
        }
        
        if (database.maintenance[gameType]) {
            return bot.sendMessage(chatId, `🔧 𝐆𝐀𝐌𝐄 ${text.toUpperCase()} Đ𝐀𝐍𝐆 𝐓𝐑𝐎𝐍𝐆 𝐐𝐔𝐀́ 𝐓𝐑𝐈̀𝐍𝐇 𝐁𝐀̉𝐎 𝐓𝐑𝐈̀!
╔════════════════════════════════════╗
║  ⏰ Vui lòng quay lại sau!
║  🙏 Cảm ơn bạn đã thông cảm!
╚════════════════════════════════════╝`);
        }
        
        if (autoPredictIntervals.has(chatId)) {
            clearInterval(autoPredictIntervals.get(chatId));
            autoPredictIntervals.delete(chatId);
        }
        
        activeGames.set(chatId, { type: gameType, name: text });
        
        const autoPredict = database.userSettings[chatId]?.autoPredict || false;
        
        if (autoPredict) {
            await updateGamePrediction(chatId, gameType, true);
            
            const interval = setInterval(async () => {
                if (activeGames.get(chatId)?.type === gameType && checkKey(chatId)) {
                    await updateGamePrediction(chatId, gameType, false);
                } else {
                    clearInterval(interval);
                    autoPredictIntervals.delete(chatId);
                }
            }, config.UPDATE_INTERVAL);
            autoPredictIntervals.set(chatId, interval);
            await bot.sendMessage(chatId, "🤖 𝐀𝐔𝐓𝐎 𝐃𝐔̛̣ Đ𝐎𝐀́𝐍 𝐃𝐀̃ 𝐁𝐀̣̂𝐓!\n📌 Sẽ tự động cập nhật khi có phiên mới!", getGameControlMenu());
        } else {
            await updateGamePrediction(chatId, gameType, true);
            await bot.sendMessage(chatId, "✅ 𝐃𝐀̃ 𝐆𝐔̛̉𝐈 𝐃𝐔̛̣ Đ𝐎𝐀́𝐍!", {
                reply_markup: {
                    keyboard: [
                        [{ text: '🎲 TÀI XỈU THƯỜNG' }, { text: '⚡ TÀI XỈU MD5' }],
                        [{ text: '🎰 TÀI XỈU SICBO' }, { text: '🔙 QUAY LẠI MENU' }]
                    ],
                    resize_keyboard: true
                }
            });
        }
    }
});

function getGameListForMaintenance() {
    const games = [
        { name: '🌸 SUNWIN', type: 'sunwin' },
        { name: '🎲 SICBO SUNWIN', type: 'sicbo_sunwin' },
        { name: '🎲 SIC789', type: 'sic789' },
        { name: '🎲 GAME789', type: 'game789' },
        { name: '⚡ BETVIP TX', type: 'betvip_tx' },
        { name: '⚡ BETVIP MD5', type: 'betvip_md5' },
        { name: '👑 LC79 TX', type: 'lc79_tx' },
        { name: '🔥 LC79 MD5', type: 'lc79_md5' },
        { name: '🎯 XOCDIA88 TX', type: 'xocdia88_tx' },
        { name: '🎯 XOCDIA88 MD5', type: 'xocdia88_md5' },
        { name: '🐉 XENG LIVE TX', type: 'xenglive_tx' },
        { name: '🐉 XENG LIVE MD5', type: 'xenglive_md5' },
        { name: '💣 B52 MD5', type: 'b52_md5' },
        { name: '🔥 HITCLUB TX', type: 'hitclub_tx' },
        { name: '💎 HITCLUB MD5', type: 'hitclub_md5' },
        { name: '🍀 LUCK8 TX', type: 'luck8_tx' },
        { name: '🍀 LUCK8 MD5', type: 'luck8_md5' },
        { name: '⭐ HAYWIN TX', type: 'haywin_tx' },
        { name: '⭐ HAYWIN MD5', type: 'haywin_md5' },
        { name: '🎰 SON789 TX', type: 'son789_tx' },
        { name: '🎰 SON789 MD5', type: 'son789_md5' },
        { name: '🔥 HOT789 TX', type: 'hot789_tx' },
        { name: '🔥 HOT789 MD5', type: 'hot789_md5' }
    ];
    
    const keyboard = [];
    let row = [];
    for (const game of games) {
        const status = database.maintenance[game.type] ? '🔴' : '🟢';
        row.push({ text: `${status} ${game.name}`, callback_data: `maintain_${game.type}` });
        if (row.length === 2) { keyboard.push(row); row = []; }
    }
    if (row.length > 0) keyboard.push(row);
    keyboard.push([{ text: "❌ THOÁT", callback_data: "maintain_exit" }]);
    return keyboard;
}

bot.on('callback_query', async (q) => {
    const chatId = q.from.id;
    const data = q.data;
    
    if (data === 'auto_on') {
        if (!database.userSettings[chatId]) database.userSettings[chatId] = {};
        database.userSettings[chatId].autoPredict = true;
        saveDB();
        await bot.sendMessage(chatId, "✅ 𝐁𝐀̣̂𝐓 𝐀𝐔𝐓𝐎 𝐃𝐔̛̣ Đ𝐎𝐀́𝐍 𝐓𝐇𝐀̀𝐍𝐇 𝐂𝐎̂𝐍𝐆!\n📌 Khi chọn game sẽ tự động cập nhật phiên mới!");
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data === 'auto_off') {
        if (!database.userSettings[chatId]) database.userSettings[chatId] = {};
        database.userSettings[chatId].autoPredict = false;
        saveDB();
        await bot.sendMessage(chatId, "✅ 𝐓𝐀̆́𝐓 𝐀𝐔𝐓𝐎 𝐃𝐔̛̣ Đ𝐎𝐀́𝐍 𝐓𝐇𝐀̀𝐍𝐇 𝐂𝐎̂𝐍𝐆!\n📌 Khi chọn game chỉ gửi dự đoán 1 lần!");
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data === 'broadcast_confirm') {
        if (Number(chatId) !== config.ADMIN_ID) return;
        
        const broadcast = database.pendingBroadcast[chatId];
        if (!broadcast || !broadcast.content) {
            await bot.sendMessage(chatId, "❌ Không có nội dung thông báo nào!");
            await bot.answerCallbackQuery(q.id);
            return;
        }
        
        const content = broadcast.content;
        const users = Object.keys(database.users);
        let successCount = 0;
        let failCount = 0;
        
        const broadcastMsg = `📢 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 𝐓𝐔̛̀ 𝐀𝐃𝐌𝐈𝐍
╔════════════════════════════════════╗
║  ${content}
╚════════════════════════════════════╝
⏰ ${new Date().toLocaleString('vi-VN')}`;
        
        await bot.sendMessage(chatId, "📢 Đang gửi thông báo đến tất cả người dùng...");
        
        for (const userId of users) {
            if (Number(userId) !== config.ADMIN_ID) {
                try {
                    await bot.sendMessage(userId, broadcastMsg);
                    successCount++;
                } catch (e) {
                    failCount++;
                }
            }
        }
        
        delete database.pendingBroadcast[chatId];
        saveDB();
        
        const resultMsg = `✅ 𝐆𝐔̛̉𝐈 𝐓𝐇𝐎̂𝐍𝐆 𝐁𝐀́𝐎 𝐓𝐇𝐀̀𝐍𝐇 𝐂𝐎̂𝐍𝐆!
╔════════════════════════════════════╗
║  ✅ Thành công: ${successCount} người
║  ❌ Thất bại: ${failCount} người
║  📝 Nội dung: ${content}
╚════════════════════════════════════╝`;
        
        await bot.sendMessage(chatId, resultMsg);
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data === 'broadcast_cancel') {
        if (Number(chatId) !== config.ADMIN_ID) return;
        delete database.pendingBroadcast[chatId];
        saveDB();
        await bot.sendMessage(chatId, "❌ Đã hủy gửi thông báo!");
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data.startsWith('gen_') && Number(chatId) === config.ADMIN_ID) {
        const type = data.split('_')[1];
        let days = 0, price = 0, typeLabel = '';
        switch(type) {
            case '1day': days = 1; price = 35000; typeLabel = '1 NGÀY'; break;
            case '3day': days = 3; price = 50000; typeLabel = '3 NGÀY'; break;
            case '7day': days = 7; price = 75000; typeLabel = '7 NGÀY'; break;
            case '30day': days = 30; price = 125000; typeLabel = '30 NGÀY'; break;
            case 'forever': days = 0; price = 170000; typeLabel = 'VĨNH VIỄN'; break;
        }
        const k = generateRandomKey(type === 'forever' ? 'forever' : 'normal');
        database.keys.push({ code: k, days: days, type: type === 'forever' ? 'forever' : 'normal', price: price });
        saveDB();
        
        const keyMsg = `🎁 𝐊𝐄𝐘 ${typeLabel} 𝐕𝐔̛̀𝐀 𝐓𝐀̣𝐎
╔════════════════════════════════════╗
║  🔑 KEY: ${k}
║  📅 HẠN: ${typeLabel}
║  💰 GIÁ: ${price.toLocaleString()} VNĐ
╚════════════════════════════════════╝`;
        
        await bot.sendMessage(chatId, keyMsg);
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data.startsWith('buykey_')) {
        const type = data.split('_')[1];
        if (type === 'huy') {
            await bot.sendMessage(chatId, "❌ Đã hủy mua key!");
            await bot.answerCallbackQuery(q.id);
            return;
        }
        let days = 0, price = 0, typeLabel = '';
        switch(type) {
            case '1day': days = 1; price = 35000; typeLabel = '1 NGÀY'; break;
            case '3day': days = 3; price = 50000; typeLabel = '3 NGÀY'; break;
            case '7day': days = 7; price = 75000; typeLabel = '7 NGÀY'; break;
            case '30day': days = 30; price = 125000; typeLabel = '30 NGÀY'; break;
            case 'forever': days = 0; price = 170000; typeLabel = 'VĨNH VIỄN'; break;
        }
        const userBalance = database.users[chatId]?.balance || 0;
        if (userBalance >= price) {
            database.users[chatId].balance = userBalance - price;
            const newKey = generateRandomKey(type === 'forever' ? 'forever' : 'normal');
            database.keys.push({ code: newKey, days: days, type: type === 'forever' ? 'forever' : 'normal', price: price });
            saveDB();
            
            const successMsg = `✅ 𝐌𝐔𝐀 𝐊𝐄𝐘 𝐓𝐇𝐀̀𝐍𝐇 𝐂𝐎̂𝐍𝐆!
╔════════════════════════════════════╗
║  🎁 GÓI: ${typeLabel}
║  🔑 KEY: ${newKey}
║  💵 DƯ: ${database.users[chatId].balance.toLocaleString()} VNĐ
╚════════════════════════════════════╝

📌 Vào "🔑 NHẬP KEY" để kích hoạt!`;
            
            await bot.sendMessage(chatId, successMsg);
        } else {
            const errorMsg = `❌ 𝐌𝐔𝐀 𝐊𝐄𝐘 𝐓𝐇𝐀̂́𝐓 𝐁𝐀̣𝐈!
╔════════════════════════════════════╗
║  💰 CẦN: ${price.toLocaleString()} VNĐ
║  💵 BẠN CÓ: ${userBalance.toLocaleString()} VNĐ
║  📌 THIẾU: ${(price - userBalance).toLocaleString()} VNĐ
╚════════════════════════════════════╝`;
            await bot.sendMessage(chatId, errorMsg);
        }
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data === 'nap_chuyenkhoan') {
        database.pendingBankDeposit[chatId] = { step: 'waiting_amount' };
        saveDB();
        await bot.sendMessage(chatId, "💰 𝐍𝐇𝐀̣̂𝐏 𝐒𝐎̂́ 𝐓𝐈𝐄̂̀𝐍 𝐂𝐀̂̀𝐍 𝐍𝐀̣𝐏\n────────────────────\n📝 Vui lòng nhập số tiền (VD: 100000):");
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data.startsWith('da_chuyen_')) {
        const depositId = data.replace('da_chuyen_', '');
        const bankInfo = database.pendingBankDeposit[chatId];
        
        if (!bankInfo || bankInfo.depositId !== depositId) {
            await bot.sendMessage(chatId, "❌ Đơn hàng không tồn tại hoặc đã được xử lý!");
            await bot.answerCallbackQuery(q.id);
            return;
        }
        
        database.pendingDeposits[depositId] = {
            userId: chatId,
            type: 'bank',
            content: bankInfo.content,
            amount: bankInfo.amount,
            username: q.from.username,
            time: Date.now(),
            status: 'pending'
        };
        
        delete database.pendingBankDeposit[chatId];
        saveDB();
        
        await bot.sendMessage(chatId, `✅ 𝐃𝐀̃ 𝐆𝐇𝐈 𝐍𝐇𝐀̣̂𝐍!
╔════════════════════════════════════╗
║  🆔 MÃ ĐƠN: ${depositId}
║  💰 SỐ TIỀN: ${bankInfo.amount.toLocaleString()} VNĐ
║  ⏰ Vui lòng đợi admin duyệt!
╚════════════════════════════════════╝`);
        
        const adminMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${q.from.first_name || ''} ${q.from.last_name || ''}
🌐 Username: @${q.from.username || 'không có'}
🆔 ID User: ${chatId}

💰 Số tiền nạp: ${bankInfo.amount.toLocaleString()} VNĐ
📝 Nội dung CK: ${bankInfo.content}
🔑 Mã Giao Dịch: ${depositId}

⏳ TRẠNG THÁI: CHỜ DUYỆT`;
        
        await bot.sendMessage(config.ADMIN_ID, adminMsg, {
            reply_markup: {
                inline_keyboard: [
                    [{ text: "✅ DUYỆT", callback_data: `duyet_bank_${depositId}_${bankInfo.amount}` }],
                    [{ text: "❌ HỦY", callback_data: `huy_${depositId}` }]
                ]
            }
        });
        
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    // ================= DUYỆT NẠP BANK =================
    if (data.startsWith('duyet_bank_')) {
        if (Number(chatId) !== config.ADMIN_ID) {
            await bot.answerCallbackQuery(q.id, { text: "⚠️ Bạn không có quyền!" });
            return;
        }
        const parts = data.split('_');
        const depositId = parts[2];
        const amount = parseInt(parts[3]);
        const deposit = database.pendingDeposits[depositId];
        
        if (deposit && deposit.status === 'pending') {
            const userId = deposit.userId;
            if (!database.users[userId]) database.users[userId] = { balance: 0 };
            database.users[userId].balance = (database.users[userId].balance || 0) + amount;
            deposit.status = 'approved';
            saveDB();
            
            const userInfo = database.users[userId]?.info || {};
            const fullName = userInfo.fullName || `${userInfo.firstName || ''} ${userInfo.lastName || ''}`.trim() || 'Người dùng';
            const username = userInfo.username || 'không có username';
            
            const adminSuccessMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${userId}

💰 Số tiền nạp: ${amount.toLocaleString()} VNĐ
📝 Nội dung CK: ${deposit.content || 'Không có'}
🔑 Mã Giao Dịch: ${depositId}

✅ TRẠNG THÁI: ĐÃ DUYỆT`;
            
            await bot.sendMessage(config.ADMIN_ID, adminSuccessMsg);
            
            const userSuccessMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${userId}

💰 Số tiền nạp: ${amount.toLocaleString()} VNĐ
📝 Nội dung CK: ${deposit.content || 'Không có'}
🔑 Mã Giao Dịch: ${depositId}

✅ TRẠNG THÁI: ĐÃ DUYỆT

💵 Số dư hiện tại: ${database.users[userId].balance.toLocaleString()} VNĐ`;
            
            await bot.sendMessage(userId, userSuccessMsg);
            
            await bot.answerCallbackQuery(q.id, { text: "✅ Đã duyệt!" });
        }
        return;
    }
    
    // ================= DUYỆT NẠP THẺ CÀO =================
    if (data.startsWith('duyet_card_')) {
        if (Number(chatId) !== config.ADMIN_ID) return;
        const parts = data.split('_');
        const depositId = parts[2];
        const amount = parseInt(parts[3]);
        const deposit = database.pendingDeposits[depositId];
        
        if (deposit && deposit.status === 'pending') {
            const userId = deposit.userId;
            if (!database.users[userId]) database.users[userId] = { balance: 0 };
            database.users[userId].balance = (database.users[userId].balance || 0) + amount;
            deposit.status = 'approved';
            saveDB();
            
            const userInfo = database.users[userId]?.info || {};
            const fullName = userInfo.fullName || `${userInfo.firstName || ''} ${userInfo.lastName || ''}`.trim() || 'Người dùng';
            const username = userInfo.username || 'không có username';
            
            const adminSuccessMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${userId}

💰 Số tiền nạp: ${amount.toLocaleString()} VNĐ
📱 Hình thức: THẺ CÀO (${deposit.provider || 'Không xác định'})
🔑 Mã Giao Dịch: ${depositId}

✅ TRẠNG THÁI: ĐÃ DUYỆT`;
            
            await bot.sendMessage(config.ADMIN_ID, adminSuccessMsg);
            
            const userSuccessMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${userId}

💰 Số tiền nạp: ${amount.toLocaleString()} VNĐ
📱 Hình thức: THẺ CÀO (${deposit.provider || 'Không xác định'})
🔑 Mã Giao Dịch: ${depositId}

✅ TRẠNG THÁI: ĐÃ DUYỆT

💵 Số dư hiện tại: ${database.users[userId].balance.toLocaleString()} VNĐ`;
            
            await bot.sendMessage(userId, userSuccessMsg);
            
            await bot.answerCallbackQuery(q.id, { text: "✅ Đã duyệt!" });
        }
        return;
    }
    
    if (data.startsWith('huy_')) {
        if (Number(chatId) !== config.ADMIN_ID) {
            await bot.answerCallbackQuery(q.id, { text: "⚠️ Bạn không có quyền!" });
            return;
        }
        const depositId = data.replace('huy_', '');
        const deposit = database.pendingDeposits[depositId];
        if (deposit && deposit.status === 'pending') {
            deposit.status = 'rejected';
            saveDB();
            
            const userInfo = database.users[deposit.userId]?.info || {};
            const fullName = userInfo.fullName || `${userInfo.firstName || ''} ${userInfo.lastName || ''}`.trim() || 'Người dùng';
            const username = userInfo.username || 'không có username';
            
            const adminCancelMsg = `❌ [ĐƠN NẠP TIỀN ĐÃ HỦY]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${deposit.userId}

💰 Số tiền: ${deposit.amount?.toLocaleString() || '?'} VNĐ
🔑 Mã Giao Dịch: ${depositId}

❌ TRẠNG THÁI: ĐÃ HỦY
⏰ Thời gian: ${new Date().toLocaleString('vi-VN')}`;
            
            await bot.sendMessage(config.ADMIN_ID, adminCancelMsg);
            await bot.sendMessage(deposit.userId, `❌ 𝐍𝐀̣𝐏 𝐓𝐈𝐄̂̀𝐍 𝐓𝐇𝐀̂́𝐓 𝐁𝐀̣𝐈!
╔════════════════════════════════════╗
║  🆔 Mã đơn: ${depositId}
║  ⚠️ Giao dịch không hợp lệ!
╚════════════════════════════════════╝`);
            
            await bot.answerCallbackQuery(q.id, { text: "❌ Đã hủy!" });
        }
        return;
    }
    
    if (data.startsWith('duyet_don_')) {
        if (Number(chatId) !== config.ADMIN_ID) return;
        const depositId = data.replace('duyet_don_', '');
        const deposit = database.pendingDeposits[depositId];
        
        if (deposit && deposit.status === 'pending') {
            await bot.sendMessage(config.ADMIN_ID, `💰 Nhập số tiền cần duyệt cho đơn ${depositId}:`);
            global.waitingAmount = depositId;
        } else {
            await bot.sendMessage(config.ADMIN_ID, `❌ Đơn ${depositId} không tồn tại hoặc đã xử lý!`);
        }
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data.startsWith('huy_don_admin_')) {
        if (Number(chatId) !== config.ADMIN_ID) return;
        const depositId = data.replace('huy_don_admin_', '');
        const deposit = database.pendingDeposits[depositId];
        if (deposit && deposit.status === 'pending') {
            deposit.status = 'rejected';
            saveDB();
            
            const userInfo = database.users[deposit.userId]?.info || {};
            const fullName = userInfo.fullName || `${userInfo.firstName || ''} ${userInfo.lastName || ''}`.trim() || 'Người dùng';
            const username = userInfo.username || 'không có username';
            
            const adminCancelMsg = `❌ [ĐƠN NẠP TIỀN ĐÃ HỦY]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${deposit.userId}

💰 Số tiền: ${deposit.amount?.toLocaleString() || '?'} VNĐ
🔑 Mã Giao Dịch: ${depositId}

❌ TRẠNG THÁI: ĐÃ HỦY`;
            
            await bot.sendMessage(config.ADMIN_ID, adminCancelMsg);
            await bot.sendMessage(deposit.userId, `❌ 𝐍𝐀̣𝐏 𝐓𝐈𝐄̂̀𝐍 𝐓𝐇𝐀̂́𝐓 𝐁𝐀̣𝐈!
╔════════════════════════════════════╗
║  🆔 Mã đơn: ${depositId}
║  ⚠️ Giao dịch không hợp lệ!
╚════════════════════════════════════╝`);
            
            await bot.answerCallbackQuery(q.id, { text: "❌ Đã hủy!" });
        }
        return;
    }
    
    if (data === 'nap_thecao') {
        database.pendingCardDeposit[chatId] = { step: 'waiting_provider' };
        saveDB();
        await bot.sendMessage(chatId, "📱 𝐂𝐇𝐎̣𝐍 𝐍𝐇𝐀̀ 𝐌𝐀̣𝐍𝐆:\nVIETTEL\nVINAPHONE\nMOBIFONE");
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data === 'nap_huy') {
        if (database.pendingBankDeposit[chatId]) delete database.pendingBankDeposit[chatId];
        if (database.pendingCardDeposit[chatId]) delete database.pendingCardDeposit[chatId];
        saveDB();
        await bot.sendMessage(chatId, "❌ Đã hủy giao dịch nạp tiền!");
        await bot.answerCallbackQuery(q.id);
        return;
    }
    
    if (data.startsWith('maintain_')) {
        if (Number(chatId) !== config.ADMIN_ID) {
            await bot.answerCallbackQuery(q.id, { text: "⚠️ Bạn không có quyền!" });
            return;
        }
        if (data === 'maintain_exit') {
            await bot.sendMessage(chatId, "🔧 Đã thoát bảo trì game!");
            await bot.answerCallbackQuery(q.id);
            return;
        }
        const gameType = data.split('_')[1];
        database.maintenance[gameType] = !database.maintenance[gameType];
        saveDB();
        const status = database.maintenance[gameType] ? "🔴 ĐANG BẢO TRÌ" : "🟢 HOẠT ĐỘNG";
        await bot.sendMessage(chatId, `✅ Đã cập nhật game: ${status}`);
        await bot.answerCallbackQuery(q.id);
        return;
    }
});

bot.on('message', async (msg) => {
    if (msg.chat.id !== config.ADMIN_ID) return;
    if (global.waitingAmount && !isNaN(msg.text)) {
        const amount = parseInt(msg.text);
        const depositId = global.waitingAmount;
        const deposit = database.pendingDeposits[depositId];
        
        if (deposit && deposit.status === 'pending') {
            const userId = deposit.userId;
            if (!database.users[userId]) database.users[userId] = { balance: 0 };
            database.users[userId].balance = (database.users[userId].balance || 0) + amount;
            deposit.status = 'approved';
            deposit.amount = amount;
            saveDB();
            
            const userInfo = database.users[userId]?.info || {};
            const fullName = userInfo.fullName || `${userInfo.firstName || ''} ${userInfo.lastName || ''}`.trim() || 'Người dùng';
            const username = userInfo.username || 'không có username';
            
            const adminSuccessMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${userId}

💰 Số tiền nạp: ${amount.toLocaleString()} VNĐ
📝 Nội dung CK: ${deposit.content || 'Không có'}
🔑 Mã Giao Dịch: ${depositId}

✅ TRẠNG THÁI: ĐÃ DUYỆT`;
            
            await bot.sendMessage(config.ADMIN_ID, adminSuccessMsg);
            
            const userSuccessMsg = `🔔 [ĐƠN NẠP TIỀN MỚI]

👤 Người dùng: ${fullName}
🌐 Username: @${username}
🆔 ID User: ${userId}

💰 Số tiền nạp: ${amount.toLocaleString()} VNĐ
📝 Nội dung CK: ${deposit.content || 'Không có'}
🔑 Mã Giao Dịch: ${depositId}

✅ TRẠNG THÁI: ĐÃ DUYỆT

💵 Số dư hiện tại: ${database.users[userId].balance.toLocaleString()} VNĐ`;
            
            await bot.sendMessage(userId, userSuccessMsg);
        }
        delete global.waitingAmount;
    }
});

console.log("🚀 𝐁𝐎𝐓 Đ𝐀̃ 𝐂𝐇𝐀̣𝐘 𝐓𝐇𝐀̀𝐍𝐇 𝐂𝐎̂𝐍𝐆!");
console.log("📌 ADMIN ID: " + config.ADMIN_ID);
console.log("🎮 Danh sách game:");
console.log("   📁 TÀI XỈU THƯỜNG: SUNWIN, B52 MD5, LC79 TX, HITCLUB TX, BETVIP TX, XOCDIA88 TX, LUCK8 TX, HAYWIN TX, SON789 TX, HOT789 TX, XENG LIVE TX");
console.log("   📁 TÀI XỈU MD5: BETVIP MD5, LC79 MD5, XOCDIA88 MD5, XENG LIVE MD5, LUCK8 MD5, HAYWIN MD5, SON789 MD5, HOT789 MD5, HITCLUB MD5");
console.log("   📁 TÀI XỈU SICBO: SICBO SUNWIN, SIC789, GAME789");