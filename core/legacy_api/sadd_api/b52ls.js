const express = require("express");
const cors = require("cors");
const axios = require("axios");

const app = express();
app.use(cors());

const PORT = process.env.PORT || 3002;
const SELF_URL = process.env.SELF_URL || `http://localhost:${PORT}`;

let latestResult = {
  Phien: 0,
  Xuc_xac_1: 0,
  Xuc_xac_2: 0,
  Xuc_xac_3: 0,
  Tong: 0,
  Ket_qua: "",
};

let history = [];

function updateResult(d1, d2, d3, sid = null) {
  const total = d1 + d2 + d3;
  const result = total > 10 ? "Tài" : "Xỉu";
  const timeStr = new Date().toISOString().replace("T", " ").slice(0, 19);

  latestResult = {
    Phien: sid || latestResult.Phien,
    Xuc_xac_1: d1,
    Xuc_xac_2: d2,
    Xuc_xac_3: d3,
    Tong: total,
    Ket_qua: result,
    id: "@mryanhdz",
    Thoi_gian: timeStr
  };

  history.unshift({...latestResult});

  if (history.length > 100) {
    history = history.slice(0, 100);
  }

  console.log(
    `[🎲✅] Phiên ${latestResult.Phien} - ${d1}-${d2}-${d3} ➜ Tổng: ${total}, Kết quả: ${result} | ${timeStr}`
  );
}

const API_TARGET_URL = 'https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=b5&gid=vgmn_101';

async function fetchGameData() {
  try {
    const response = await axios.get(API_TARGET_URL);
    const data = response.data;

    if (data.status === "OK" && Array.isArray(data.data) && data.data.length > 0) {
      const game = data.data[0];
      const sid = game.sid;
      const d1 = game.d1;
      const d2 = game.d2;
      const d3 = game.d3;

      if (sid !== latestResult.Phien && d1 !== undefined && d2 !== undefined && d3 !== undefined) {
        updateResult(d1, d2, d3, sid);
      }
    }
  } catch (error) {
    console.error("❌ Lỗi khi lấy dữ liệu từ API GET:", error.message);
  }
}

setInterval(fetchGameData, 5000);

app.get("/api/ditmemayb52", (req, res) => {
  res.json(latestResult);
});

app.get("/api/history", (req, res) => {
  res.json({
    total: history.length,
    data: history
  });
});

app.get("/", (req, res) => {
  res.json({ status: "B52 Tài Xỉu đang chạy", phien: latestResult.Phien, total_history: history.length });
});

setInterval(() => {
  if (SELF_URL.includes("http")) {
    axios.get(`${SELF_URL}/api/ditmemayb52`).catch(() => {});
  }
}, 300000);

app.listen(PORT, () => {
  console.log(`🚀 Server B52 Tài Xỉu đang chạy tại http://localhost:${PORT}`);
});