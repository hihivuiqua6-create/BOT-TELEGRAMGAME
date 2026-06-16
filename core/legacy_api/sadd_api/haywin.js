const ai = require('../ai_engine');
// server.js
// Advanced Markov / Pattern Analyzer - educational/research use only
// Không dùng cho mục đích đánh bạc/chiếm ưu thế trong TX

const express = require('express');
const axios = require('axios');
const app = express();
const PORT = process.env.PORT || 8000;

const POLL_INTERVAL = 5000;
const RETRY_DELAY = 5000;
const MAX_HISTORY = 1000; // lưu nhiều để phân tích pattern
const ID_TAG = "@tiendataox";

let latest_result_100 = {
  Phien: 0,
  Xuc_xac_1: 0,
  Xuc_xac_2: 0,
  Xuc_xac_3: 0,
  Tong_diem: 0,
  Pattern: "Chưa có",
  Phien_hien_tai: 0,
  Du_doan: "Chưa có",
  Tong_du_doan: 0,
  Tong_thang: 0,
  Tong_thua: 0,
  Id: ID_TAG
};

// Bàn MD5 (gid=101)
let latest_result_101 = {
  Phien: 0,
  Xuc_xac_1: 0,
  Xuc_xac_2: 0,
  Xuc_xac_3: 0,
  Tong_diem: 0,
  Pattern: "Chưa có",
  Phien_hien_tai: 0,
  Du_doan: "Chưa có",
  Tong_du_doan: 0,
  Tong_thang: 0,
  Tong_thua: 0,
  Id: ID_TAG
};

let history_100 = [];
let history_101 = [];
let last_sid_100 = null;
let last_sid_101 = null;
let sid_for_tx = null;

// global stats cho từng bàn
let globalStats = {
  ban_tai_xiu: {
    totalPredictions: 0,
    totalWins: 0,
    totalLosses: 0
  },
  ban_md5: {
    totalPredictions: 0,
    totalWins: 0,
    totalLosses: 0
  }
};

/**
 * AdvancedMarkovAnalyzer
 * - order: N-order Markov (supports N>=1)
 * - decay: recency weight factor, 0..1 (1 = no decay, recent => recent events weigh more)
 * - laplace: smoothing parameter (alpha)
 * - memories: array of memory window sizes for ensemble (e.g. [3,10,50])
 */
class AdvancedMarkovAnalyzer {
  constructor({
    states = ['Tài','Xỉu'],
    order = 2,
    decay = 0.98,
    laplace = 1,
    memories = [3,10,50],
    maxHistory = 1000
  } = {}) {
    this.states = states;
    this.order = Math.max(1, order);
    this.decay = decay;
    this.laplace = laplace;
    this.memories = memories;
    this.maxHistory = maxHistory;

    // transitionCounts: map from context string -> { state: weightedCount }
    // e.g. { "Tài|Xỉu": { "Tài": 5.2, "Xỉu": 2.1 } }
    this.transitionCounts = new Map();

    // frequency counts for patterns (sliding)
    this.patternFreq = new Map();

    // full raw history as array of states (most recent at end)
    this.rawHistory = [];

    // predictions history: Map phien -> { prediction, timestamp, probs }
    this.predictionHistory = new Map();
  }

  // helper: context key from array of previous states
  contextKey(prevStates) {
    return prevStates.join('|');
  }

  // apply decay to all stored counts (to implement recency weighting)
  applyDecayToAll() {
    const decayFactor = this.decay;
    for (const [ctx, counts] of this.transitionCounts.entries()) {
      const newCounts = {};
      let total = 0;
      for (const s of this.states) {
        const v = (counts[s] || 0) * decayFactor;
        newCounts[s] = v;
        total += v;
      }
      // remove if extremely small to free memory
      if (total < 1e-6) {
        this.transitionCounts.delete(ctx);
      } else {
        this.transitionCounts.set(ctx, newCounts);
      }
    }

    // decay pattern frequencies
    for (const [pat, cnt] of this.patternFreq.entries()) {
      const v = cnt * decayFactor;
      if (v < 1e-6) this.patternFreq.delete(pat);
      else this.patternFreq.set(pat, v);
    }
  }

  // update model with a new actual state (string)
  update(actualState) {
    if (!this.states.includes(actualState)) {
      throw new Error("Unknown state: " + actualState);
    }

    // append to rawHistory
    this.rawHistory.push(actualState);
    if (this.rawHistory.length > this.maxHistory) {
      this.rawHistory.shift();
    }

    // update pattern frequencies for contexts up to order
    const L = this.rawHistory.length;
    const maxPat = Math.min(this.order, L);
    for (let patLen = 1; patLen <= maxPat; patLen++) {
      const seq = this.rawHistory.slice(L - patLen, L).join('|');
      const prev = this.patternFreq.get(seq) || 0;
      this.patternFreq.set(seq, prev + 1);
    }

    // update transition counts for all contexts up to order (use previous tokens)
    for (let k = 1; k <= this.order; k++) {
      if (this.rawHistory.length - 1 - (k - 1) < 0) break;
      const ctxStart = this.rawHistory.length - 1 - (k);
      if (ctxStart < 0) continue;
      const ctx = this.rawHistory.slice(ctxStart, ctxStart + k).join('|');
      const counts = this.transitionCounts.get(ctx) || {};
      counts[actualState] = (counts[actualState] || 0) + 1;
      this.transitionCounts.set(ctx, counts);
    }

    // periodic decay to enforce recency weights
    // apply decay occasionally to avoid O(N) each update; here we do every 20 updates
    if (this.rawHistory.length % 20 === 0) {
      this.applyDecayToAll();
    }
  }

  // get smoothed probabilities for a given context (string)
  getProbabilitiesForContext(ctx) {
    // Laplace smoothing: P(s|ctx) = (count(ctx -> s) + alpha) / (sum_counts + alpha * K)
    const counts = this.transitionCounts.get(ctx) || {};
    let sum = 0;
    for (const s of this.states) sum += (counts[s] || 0);
    const K = this.states.length;
    const probs = {};
    for (const s of this.states) {
      const c = (counts[s] || 0);
      probs[s] = (c + this.laplace) / (sum + this.laplace * K);
    }
    return probs;
  }

  // Predict next using ensemble across memory windows and orders
  predictEnsemble() {
    // compute ensemble probability vector
    const aggregate = {};
    for (const s of this.states) aggregate[s] = 0;

    const L = this.rawHistory.length;
    if (L === 0) {
      // no data -> uniform
      const uniform = 1 / this.states.length;
      for (const s of this.states) aggregate[s] = uniform;
      return { probs: aggregate, chosen: this.states[0], confidence: 0 };
    }

    // For each memory window, compute context and weight
    // weight scheme: larger memory may get different weight; we'll use memoryWeight = log(memory+e)
    for (const mem of this.memories) {
      const memSize = Math.min(mem, L);
      // choose order up to this.order but not exceeding memSize
      const orderForMem = Math.min(this.order, memSize);
      const ctx = this.rawHistory.slice(L - orderForMem, L).join('|');
      const probs = this.getProbabilitiesForContext(ctx);

      // weight by recency of that memory: more recent (smaller mem) -> slightly higher importance
      // weight formula: w = 1 / (1 + log(mem))
      const weight = 1 / (1 + Math.log(1 + mem));

      for (const s of this.states) {
        aggregate[s] += probs[s] * weight;
      }
    }

    // normalize aggregate
    let total = 0;
    for (const s of this.states) total += aggregate[s];
    if (total <= 0) {
      const uniform = 1 / this.states.length;
      for (const s of this.states) aggregate[s] = uniform;
    } else {
      for (const s of this.states) aggregate[s] /= total;
    }

    // choose highest probability
    let chosen = this.states[0];
    let best = aggregate[chosen];
    for (const s of this.states) {
      if (aggregate[s] > best) {
        best = aggregate[s];
        chosen = s;
      }
    }

    const confidence = Math.abs(aggregate[this.states[0]] - aggregate[this.states[1]]);

    return { probs: aggregate, chosen, confidence };
  }

  // count pattern frequencies for a given pattern (e.g., "Tài|Tài|Xỉu")
  getPatternFrequency(pattern) {
    return this.patternFreq.get(pattern) || 0;
  }

  // get top-k frequent patterns of length up to order
  topPatterns(k = 20, maxLen = undefined) {
    const arr = [];
    for (const [pat, cnt] of this.patternFreq.entries()) {
      const parts = pat.split('|');
      if (maxLen && parts.length > maxLen) continue;
      arr.push({ pattern: pat, count: cnt, length: parts.length });
    }
    arr.sort((a,b) => b.count - a.count);
    return arr.slice(0,k);
  }

  // save prediction for a phien (round)
  savePrediction(phien, result) {
    this.predictionHistory.set(phien, { ...result, timestamp: Date.now() });
    // cap stored predictions
    if (this.predictionHistory.size > 500) {
      const oldest = Array.from(this.predictionHistory.keys())[0];
      this.predictionHistory.delete(oldest);
    }
  }

  getPrediction(phien) {
    return this.predictionHistory.get(phien);
  }

  // full analysis snapshot
  getFullAnalysis() {
    const memAnalyses = {};
    for (const mem of this.memories) {
      const memSize = Math.min(mem, this.rawHistory.length);
      const orderForMem = Math.min(this.order, memSize);
      const ctx = this.rawHistory.slice(this.rawHistory.length - orderForMem, this.rawHistory.length).join('|');
      memAnalyses[`m${mem}`] = {
        context: ctx,
        probs: this.getProbabilitiesForContext(ctx)
      };
    }

    return {
      order: this.order,
      decay: this.decay,
      laplace: this.laplace,
      memories: this.memories,
      rawHistoryLength: this.rawHistory.length,
      rawHistorySample: this.rawHistory.slice(-Math.min(50, this.rawHistory.length)),
      transitionContextsStored: this.transitionCounts.size,
      topPatterns: this.topPatterns(30, this.order),
      memoryAnalyses: memAnalyses
    };
  }
}

// instantiate advanced analyzers cho từng bàn
const advanced_tx = new AdvancedMarkovAnalyzer({
  order: 3,
  decay: 0.985,
  laplace: 1,
  memories: [3, 10, 50],
  maxHistory: 2000
});

const advanced_md5 = new AdvancedMarkovAnalyzer({
  order: 3,
  decay: 0.985,
  laplace: 1,
  memories: [3, 10, 50],
  maxHistory: 2000
});

function formatBeautifulJSON(data) {
  return JSON.stringify(data, null, 2);
}

function updateResult(store, history, analyzer, stats, result, tableName) {
  Object.assign(store, result);

  // interpret actual result generically
  const actualResult = store.Tong_diem > 10 ? 'Tài' : 'Xỉu';
  store.Pattern = actualResult;

  // update analyzer with actual result (for educational/research)
  analyzer.update(actualResult);

  // predict next (ensemble)
  const pred = analyzer.predictEnsemble();
  store.Phien_hien_tai = store.Phien + 1;
  store.Du_doan = pred.chosen;
  store.Du_doan_confidence = parseFloat(pred.confidence.toFixed(3));
  store.Du_doan_probs = pred.probs;

  // save prediction record keyed by next phien
  analyzer.savePrediction(store.Phien_hien_tai, {
    prediction: pred.chosen,
    probs: pred.probs,
    confidence: pred.confidence
  });

  // evaluate previous phien prediction if exists
  if (history.length >= 1) {
    const previousGame = history[0];
    const prevPredRecord = analyzer.getPrediction(previousGame.Phien);
    if (prevPredRecord && prevPredRecord.prediction) {
      stats.totalPredictions++;
      const wasCorrect = prevPredRecord.prediction === actualResult;
      if (wasCorrect) stats.totalWins++;
      else stats.totalLosses++;

      previousGame.Tong_thang = stats.totalWins;
      previousGame.Tong_thua = stats.totalLosses;
      previousGame.Tong_du_doan = stats.totalPredictions;
      previousGame.Du_doan = prevPredRecord.prediction;
      previousGame.Danh_gia = wasCorrect ? 'Đúng' : 'Sai';

      console.log(`[${tableName}] EVAL Phiên ${previousGame.Phien} | Dự đoán: ${prevPredRecord.prediction} | Thực tế: ${actualResult} | ${wasCorrect ? '✅' : '❌'}`);
    }
  }

  // add to history (most recent first)
  const historyEntry = {
    ...result,
    Ket_qua: actualResult,
    Tong_thang: stats.totalWins,
    Tong_thua: stats.totalLosses,
    Tong_du_doan: stats.totalPredictions,
    Id: ID_TAG
  };

  history.unshift(historyEntry);
  if (history.length > MAX_HISTORY) history.pop();

  // update store summary
  store.Tong_du_doan = stats.totalPredictions;
  store.Tong_thang = stats.totalWins;
  store.Tong_thua = stats.totalLosses;
  store.Id = ID_TAG;

  // Logging brief
  console.log(`[${tableName}] 🎲 Phiên ${store.Phien} | Tổng: ${store.Tong_diem} | KQ: ${actualResult} | Dự đoán tiếp theo: ${store.Du_doan} (conf ${store.Du_doan_confidence})`);
}

async function pollTaiXiu() {
  const url = `https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=rik&gid=vgmn_100`;

  while (true) {
    try {
      const res = await axios.get(url, {
        headers: { 'User-Agent': 'Node-Proxy/1.0' },
        timeout: 10000
      });

      const data = res.data;
      if (data && data.status === 'OK' && Array.isArray(data.data)) {
        for (const game of data.data) {
          if (game.cmd === 1008) {
            sid_for_tx = game.sid;
          }
        }

        for (const game of data.data) {
          if (game.cmd === 1003) {
            const sid = sid_for_tx;
            const { d1, d2, d3 } = game;
            if (sid && sid !== last_sid_100 && [d1,d2,d3].every(x => x != null)) {
              last_sid_100 = sid;
              const total = d1 + d2 + d3;
              const result = {
                Phien: sid,
                Xuc_xac_1: d1,
                Xuc_xac_2: d2,
                Xuc_xac_3: d3,
                Tong_diem: total,
                Pattern: "",
                Du_doan: "Chưa có",
                Tong_du_doan: 0,
                Tong_thang: 0,
                Tong_thua: 0,
                Id: ID_TAG
              };

              updateResult(latest_result_100, history_100, advanced_tx, globalStats.ban_tai_xiu, result, "BÀN TÀI XỈU");

              const analysis = advanced_tx.getFullAnalysis();
              console.log('─'.repeat(60));
              console.log(`🎯 [Bàn Tài Xỉu] Analysis snapshot: order=${analysis.order}, historyLen=${analysis.rawHistoryLength}`);
              console.log(`🔮 Next prediction: ${latest_result_100.Du_doan} | Conf: ${latest_result_100.Du_doan_confidence}`);
              console.log(`📈 Top patterns sample:`, analysis.topPatterns ? analysis.topPatterns.slice(0,5) : 'n/a');
              console.log(`📊 Global wins: ${globalStats.ban_tai_xiu.totalWins}/${globalStats.ban_tai_xiu.totalPredictions}`);
              console.log('─'.repeat(60));

              sid_for_tx = null;
            }
          }
        }
      }
    } catch (err) {
      console.error("Lỗi khi lấy dữ liệu TX (bàn Tài Xỉu):", err.message || err);
      await new Promise(r => setTimeout(r, RETRY_DELAY));
    }

    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
}

// Hàm dành riêng cho bàn MD5 (đã sửa cấu trúc)
async function pollMD5() {
  const url = `https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=rik&gid=vgmn_101`;

  while (true) {
    try {
      const res = await axios.get(url, {
        headers: { 'User-Agent': 'Node-Proxy/1.0' },
        timeout: 10000
      });

      const data = res.data;
      
      // Kiểm tra cấu trúc response của bàn MD5 (cmd === 7006, có d1,d2,d3)
      if (data && data.status === 'OK' && data.data && Array.isArray(data.data)) {
        for (const game of data.data) {
          // Bàn MD5 dùng cmd 7006 để gửi kết quả, không cần cmd 1008 riêng
          if (game.cmd === 7006 && game.d1 && game.d2 && game.d3) {
            const sid = game.sid;
            
            // Kiểm tra xem đã xử lý phiên này chưa
            if (sid && sid !== last_sid_101) {
              last_sid_101 = sid;
              const total = game.d1 + game.d2 + game.d3;
              
              const result = {
                Phien: sid,
                Xuc_xac_1: game.d1,
                Xuc_xac_2: game.d2,
                Xuc_xac_3: game.d3,
                Tong_diem: total,
                Pattern: "",
                Du_doan: "Chưa có",
                Tong_du_doan: 0,
                Tong_thang: 0,
                Tong_thua: 0,
                Id: ID_TAG
              };

              // Cập nhật kết quả vào hệ thống (dùng chung hàm updateResult)
              updateResult(latest_result_101, history_101, advanced_md5, globalStats.ban_md5, result, "BÀN MD5");

              // Log phân tích cho bàn MD5
              const analysis = advanced_md5.getFullAnalysis();
              console.log('─'.repeat(60));
              console.log(`🎯 [Bàn MD5] Analysis snapshot: order=${analysis.order}, historyLen=${analysis.rawHistoryLength}`);
              console.log(`🔮 Next prediction: ${latest_result_101.Du_doan} | Conf: ${latest_result_101.Du_doan_confidence}`);
              console.log(`📈 Top patterns sample:`, analysis.topPatterns ? analysis.topPatterns.slice(0,5) : 'n/a');
              console.log(`📊 MD5 Wins: ${globalStats.ban_md5.totalWins}/${globalStats.ban_md5.totalPredictions}`);
              console.log('─'.repeat(60));
            }
          }
        }
      } else {
        // Log nếu response không đúng cấu trúc để debug
        console.log("[MD5 DEBUG] Response không đúng cấu trúc:", JSON.stringify(data).substring(0, 200));
      }
    } catch (err) {
      console.error("Lỗi khi lấy dữ liệu bàn MD5:", err.message || err);
      await new Promise(r => setTimeout(r, RETRY_DELAY));
    }

    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
}

// APIs
app.get('/api/taixiu', (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.send(formatBeautifulJSON(latest_result_100));
});

app.get('/api/md5', (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.send(formatBeautifulJSON(latest_result_101));
});

app.get('/api/history', (req, res) => {
  const lich_su = history_100.map(item => {
    return {
      Phien: item.Phien,
      Du_doan: item.Du_doan || 'Chưa có',
      Ket_qua: item.Ket_qua,
      Danh_gia: item.Danh_gia || 'Chưa đánh giá'
    };
  });

  const historyData = {
    ban: "Tài Xỉu",
    Tong_so_phien_du_doan: globalStats.ban_tai_xiu.totalPredictions,
    Tong_du_doan_dung: globalStats.ban_tai_xiu.totalWins,
    Tong_du_doan_sai: globalStats.ban_tai_xiu.totalLosses,
    lich_su: lich_su
  };

  res.setHeader('Content-Type', 'application/json');
  res.send(formatBeautifulJSON(historyData));
});

app.get('/api/history/md5', (req, res) => {
  const lich_su = history_101.map(item => {
    return {
      Phien: item.Phien,
      Du_doan: item.Du_doan || 'Chưa có',
      Ket_qua: item.Ket_qua,
      Danh_gia: item.Danh_gia || 'Chưa đánh giá'
    };
  });

  const historyData = {
    ban: "MD5",
    Tong_so_phien_du_doan: globalStats.ban_md5.totalPredictions,
    Tong_du_doan_dung: globalStats.ban_md5.totalWins,
    Tong_du_doan_sai: globalStats.ban_md5.totalLosses,
    lich_su: lich_su
  };

  res.setHeader('Content-Type', 'application/json');
  res.send(formatBeautifulJSON(historyData));
});

app.get('/api/stats', (req, res) => {
  const markovAnalysis = advanced_tx.getFullAnalysis();
  const statsData = {
    ban_tai_xiu: {
      accuracy: globalStats.ban_tai_xiu.totalPredictions > 0 ? (globalStats.ban_tai_xiu.totalWins / globalStats.ban_tai_xiu.totalPredictions * 100).toFixed(2) : 0,
      total_predictions: globalStats.ban_tai_xiu.totalPredictions,
      correct_predictions: globalStats.ban_tai_xiu.totalWins,
      incorrect_predictions: globalStats.ban_tai_xiu.totalLosses,
      current_prediction: latest_result_100.Du_doan,
      history_length: advanced_tx.rawHistory.length
    },
    ban_md5: {
      accuracy: globalStats.ban_md5.totalPredictions > 0 ? (globalStats.ban_md5.totalWins / globalStats.ban_md5.totalPredictions * 100).toFixed(2) : 0,
      total_predictions: globalStats.ban_md5.totalPredictions,
      correct_predictions: globalStats.ban_md5.totalWins,
      incorrect_predictions: globalStats.ban_md5.totalLosses,
      current_prediction: latest_result_101.Du_doan,
      history_length: advanced_md5.rawHistory.length
    },
    markov_analysis: markovAnalysis
  };

  res.setHeader('Content-Type', 'application/json');
  res.send(formatBeautifulJSON(statsData));
});

app.get('/api/markov', (req, res) => {
  const fullAnalysis = advanced_tx.getFullAnalysis();
  const markovData = {
    ban: "Tài Xỉu",
    advanced_config: {
      order: advanced_tx.order,
      decay: advanced_tx.decay,
      laplace: advanced_tx.laplace,
      memories: advanced_tx.memories
    },
    analysis: fullAnalysis,
    latest_prediction: advanced_tx.predictionHistory.size ? Array.from(advanced_tx.predictionHistory.entries()).slice(-5) : []
  };

  res.setHeader('Content-Type', 'application/json');
  res.send(formatBeautifulJSON(markovData));
});

app.get('/api/markov/md5', (req, res) => {
  const fullAnalysis = advanced_md5.getFullAnalysis();
  const markovData = {
    ban: "MD5",
    advanced_config: {
      order: advanced_md5.order,
      decay: advanced_md5.decay,
      laplace: advanced_md5.laplace,
      memories: advanced_md5.memories
    },
    analysis: fullAnalysis,
    latest_prediction: advanced_md5.predictionHistory.size ? Array.from(advanced_md5.predictionHistory.entries()).slice(-5) : []
  };

  res.setHeader('Content-Type', 'application/json');
  res.send(formatBeautifulJSON(markovData));
});

// optional endpoint to fetch the source code (for convenience)
app.get('/api/fullcode', (req, res) => {
  res.setHeader('Content-Type', 'text/plain');
  res.send("// Full code is stored on the server's filesystem. If you need the file content, fetch it directly.");
});

app.get('/', (req, res) => {
  res.send("🎲 Advanced Analyzer (educational) running. Endpoints: /api/taixiu, /api/md5, /api/history, /api/history/md5, /api/stats, /api/markov, /api/markov/md5");
});

console.log("🚀 Khởi động Advanced Analyzer (chỉ học thuật)...");
pollTaiXiu();
pollMD5();

app.listen(PORT, () => {
  console.log(`✅ Server running on port ${PORT}`);
  console.log(`📌 ID: ${ID_TAG}`);
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
