const ai = require('../ai_engine');

// AI Adaptive Engine (simple weight updater)
let aiState = {
    win: 0,
    lose: 0,
    weight: 0.5
};

function updateAI(result) {
    // result: 'win' | 'lose'
    if (result === 'win') aiState.win++;
    if (result === 'lose') aiState.lose++;

    const total = aiState.win + aiState.lose;
    if (total > 0) {
        const winRate = aiState.win / total;

        // adaptive weight (not prediction guarantee, just adjustment signal)
        aiState.weight = 0.3 + (winRate * 0.4);
    }

    return aiState.weight;
}

function getAIWeight() {
    return aiState.weight;
}

module.exports = { updateAI, getAIWeight };
