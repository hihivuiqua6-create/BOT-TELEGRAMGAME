const ai = require('../ai_engine');
// server.js
// Advanced Markov / Pattern Analyzer - educational/research use only

const express = require('express');
const axios = require('axios');
const app = express();
const PORT = process.env.PORT || 8000;

const POLL_INTERVAL = 5000;
const RETRY_DELAY = 5000;
const MAX_HISTORY = 1000;
const ID_TAG = "@tiendataox";

let latest_result_100 = {
  Phien: 0,
  Xuc_xac_1: 0,
  Xuc_xac_2: 0,
  Xuc_xac_3: 0,
  Tong_diem: 0,
  Pattern: "Chua co",
  Phien_hien_tai: 0,
  Du_doan: "Chua co",
  Tong_du_doan: 0,
  Tong_thang: 0,
  Tong_thua: 0,
  Id: ID_TAG
};

let latest_result_101 = {
  Phien: 0,
  Xuc_xac_1: 0,
  Xuc_xac_2: 0,
  Xuc_xac_3: 0,
  Tong_diem: 0,
  Pattern: "Chua co",
  Phien_hien_tai: 0,
  Du_doan: "Chua co",
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

class AdvancedMarkovAnalyzer {
  constructor({
    states = ['Tai', 'Xiu'],
    order = 2,
    decay = 0.98,
    laplace = 1,
    memories = [3, 10, 50],
    maxHistory = 1000
  } = {}) {
    this.states = states;
    this.order = Math.max(1, order);
    this.decay = decay;
    this.laplace = laplace;
    this.memories = memories;
    this.maxHistory = maxHistory;
    this.transitionCounts = new Map();
    this.patternFreq = new Map();
    this.rawHistory = [];
    this.predictionHistory = new Map();
  }

  contextKey(prevStates) {
    return prevStates.join('|');
  }

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
      if (total < 1e-6) {
        this.transitionCounts.delete(ctx);
      } else {
        this.transitionCounts.set(ctx, newCounts);
      }
    }

    for (const [pat, cnt] of this.patternFreq.entries()) {
      const v = cnt * decayFactor;
      if (v < 1e-6) this.patternFreq.delete(pat);
      else this.patternFreq.set(pat, v);
    }
  }

  update(actualState) {
    if (!this.states.includes(actualState)) {
      throw new Error("Unknown state: " + actualState);
    }

    this.rawHistory.push(actualState);
    if (this.rawHistory.length > this.maxHistory) {
      this.rawHistory.shift();
    }

    const L = this.rawHistory.length;
    const maxPat = Math.min(this.order, L);
    for (let patLen = 1; patLen <= maxPat; patLen++) {
      const seq = this.rawHistory.slice(L - patLen, L).join('|');
      const prev = this.patternFreq.get(seq) || 0;
      this.patternFreq.set(seq, prev + 1);
    }

    for (let k = 1; k <= this.order; k++) {
      if (this.rawHistory.length - 1 - (k - 1) < 0) break;
      const ctxStart = this.rawHistory.length - 1 - (k);
      if (ctxStart < 0) continue;
      const ctx = this.rawHistory.slice(ctxStart, ctxStart + k).join('|');
      const counts = this.transitionCounts.get(ctx) || {};
      counts[actualState] = (counts[actualState] || 0) + 1;
      this.transitionCounts.set(ctx, counts);
    }

    if (this.rawHistory.length % 20 === 0) {
      this.applyDecayToAll();
    }
  }

  getProbabilitiesForContext(ctx) {
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

  predictEnsemble() {
    const aggregate = {};
    for (const s of this.states) aggregate[s] = 0;

    const L = this.rawHistory.length;
    if (L === 0) {
      const uniform = 1 / this.states.length;
      for (const s of this.states) aggregate[s] = uniform;
      return { probs: aggregate, chosen: this.states[0], confidence: 0 };
    }

    for (const mem of this.memories) {
      const memSize = Math.min(mem, L);
      const orderForMem = Math.min(this.order, memSize);
      const ctx = this.rawHistory.slice(L - orderForMem, L).join('|');
      const probs = this.getProbabilitiesForContext(ctx);
      const weight = 1 / (1 + Math.log(1 + mem));

      for (const s of this.states) {
        aggregate[s] += probs[s] * weight;
      }
    }

    let total = 0;
    for (const s of this.states) total += aggregate[s];
    if (total <= 0) {
      const uniform = 1 / this.states.length;
      for (const s of this.states) aggregate[s] = uniform;
    } else {
      for (const s of this.states) aggregate[s] /= total;
    }

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

  getPatternFrequency(pattern) {
    return this.patternFreq.get(pattern) || 0;
  }

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

  savePrediction(phien, result) {
    this.predictionHistory.set(phien, { ...result, timestamp: Date.now() });
    if (this.predictionHistory.size > 500) {
      const oldest = Array.from(this.predictionHistory.keys())[0];
      this.predictionHistory.delete(oldest);
    }
  }

  getPrediction(phien) {
    return this.predictionHistory.get(phien);
  }

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

  const actualResult = store.Tong_diem > 10 ? 'Tai' : 'Xiu';
  store.Pattern = actualResult;

  analyzer.update(actualResult);

  const pred = analyzer.predictEnsemble();
  store.Phien_hien_tai = store.Phien + 1;
  store.Du_doan = pred.chosen;
  store.Du_doan_confidence = parseFloat(pred.confidence.toFixed(3));
  store.Du_doan_probs = pred.probs;

  analyzer.savePrediction(store.Phien_hien_tai, {
    prediction: pred.chosen,
    probs: pred.probs,
    confidence: pred.confidence
  });

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
      previousGame.Danh_gia = wasCorrect ? 'Dung' : 'Sai';

      console.log(`[${tableName}] EVAL Phien ${previousGame.Phien} | Du doan: ${prevPredRecord.prediction} | Thuc te: ${actualResult} | ${wasCorrect ? '✅' : '❌'}`);
    }
  }

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

  store.Tong_du_doan = stats.totalPredictions;
  store.Tong_thang = stats.totalWins;
  store.Tong_thua = stats.totalLosses;
  store.Id = ID_TAG;

  console.log(`[${tableName}] 🎲 Phien ${store.Phien} | Tong: ${store.Tong_diem} | KQ: ${actualResult} | Du doan tiep theo: ${store.Du_doan} (conf ${store.Du_doan_confidence})`);
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
                Du_doan: "Chua co",
                Tong_du_doan: 0,
                Tong_thang: 0,
                Tong_thua: 0,
                Id: ID_TAG
              };

              updateResult(latest_result_100, history_100, advanced_tx, globalStats.ban_tai_xiu, result, "BAN TAI XIU");

              const analysis = advanced_tx.getFullAnalysis();
              console.log('─'.repeat(60));
              console.log(`🎯 [Ban Tai Xiu] Analysis: order=${analysis.order}, historyLen=${analysis.rawHistoryLength}`);
              console.log(`🔮 Next prediction: ${latest_result_100.Du_doan} | Conf: ${latest_result_100.Du_doan_confidence}`);
              console.log(`📊 Wins: ${globalStats.ban_tai_xiu.totalWins}/${globalStats.ban_tai_xiu.totalPredictions}`);
              console.log('─'.repeat(60));

              sid_for_tx = null;
            }
          }
        }
      }
    } catch (err) {
      console.error("Loi khi lay du lieu TX:", err.message || err);
      await new Promise(r => setTimeout(r, RETRY_DELAY));
    }

    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
}

async function pollMD5() {
  const url = `https://jakpotgwab.geightdors.net/glms/v1/notify/taixiu?platform_id=rik&gid=vgmn_101`;

  while (true) {
    try {
      const res = await axios.get(url, {
        headers: { 'User-Agent': 'Node-Proxy/1.0' },
        timeout: 10000
      });

      const data = res.data;
      
      if (data && data.status === 'OK' && data.data && Array.isArray(data.data)) {
        for (const game of data.data) {
          if (game.cmd === 7006 && game.d1 && game.d2 && game.d3) {
            const sid = game.sid;
            
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
                Du_doan: "Chua co",
                Tong_du_doan: 0,
                Tong_thang: 0,
                Tong_thua: 0,
                Id: ID_TAG
              };

              updateResult(latest_result_101, history_101, advanced_md5, globalStats.ban_md5, result, "BAN MD5");

              const analysis = advanced_md5.getFullAnalysis();
              console.log('─'.repeat(60));
              console.log(`🎯 [Ban MD5] Analysis: order=${analysis.order}, historyLen=${analysis.rawHistoryLength}`);
              console.log(`🔮 Next prediction: ${latest_result_101.Du_doan} | Conf: ${latest_result_101.Du_doan_confidence}`);
              console.log(`📊 Wins: ${globalStats.ban_md5.totalWins}/${globalStats.ban_md5.totalPredictions}`);
              console.log('─'.repeat(60));
            }
          }
        }
      }
    } catch (err) {
      console.error("Loi khi lay du lieu MD5:", err.message || err);
      await new Promise(r => setTimeout(r, RETRY_DELAY));
    }

    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
}

// APIs
app.get('/api/taixiu', (req, res) => {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.send(formatBeautifulJSON(latest_result_100));
});

app.get('/api/md5', (req, res) => {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.send(formatBeautifulJSON(latest_result_101));
});

app.get('/api/history', (req, res) => {
  const lich_su = history_100.map(item => {
    return {
      Phien: item.Phien,
      Du_doan: item.Du_doan || 'Chua co',
      Ket_qua: item.Ket_qua,
      Danh_gia: item.Danh_gia || 'Chua danh gia'
    };
  });

  const historyData = {
    ban: "Tai Xiu",
    Tong_so_phien_du_doan: globalStats.ban_tai_xiu.totalPredictions,
    Tong_du_doan_dung: globalStats.ban_tai_xiu.totalWins,
    Tong_du_doan_sai: globalStats.ban_tai_xiu.totalLosses,
    lich_su: lich_su
  };

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.send(formatBeautifulJSON(historyData));
});

app.get('/api/history/md5', (req, res) => {
  const lich_su = history_101.map(item => {
    return {
      Phien: item.Phien,
      Du_doan: item.Du_doan || 'Chua co',
      Ket_qua: item.Ket_qua,
      Danh_gia: item.Danh_gia || 'Chua danh gia'
    };
  });

  const historyData = {
    ban: "MD5",
    Tong_so_phien_du_doan: globalStats.ban_md5.totalPredictions,
    Tong_du_doan_dung: globalStats.ban_md5.totalWins,
    Tong_du_doan_sai: globalStats.ban_md5.totalLosses,
    lich_su: lich_su
  };

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.send(formatBeautifulJSON(historyData));
});

app.get('/api/stats', (req, res) => {
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
    }
  };

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.send(formatBeautifulJSON(statsData));
});

app.get('/api/markov', (req, res) => {
  const fullAnalysis = advanced_tx.getFullAnalysis();
  const markovData = {
    ban: "Tai Xiu",
    advanced_config: {
      order: advanced_tx.order,
      decay: advanced_tx.decay,
      laplace: advanced_tx.laplace,
      memories: advanced_tx.memories
    },
    analysis: fullAnalysis
  };

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
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
    analysis: fullAnalysis
  };

  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.send(formatBeautifulJSON(markovData));
});

app.get('/', (req, res) => {
  res.send("🎲 Advanced Analyzer running. Endpoints: /api/taixiu, /api/md5, /api/history, /api/history/md5, /api/stats, /api/markov, /api/markov/md5");
});

console.log("🚀 Khoi dong Advanced Analyzer...");
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
