#!/usr/bin/env node
/**
 * 🧠 DECISION CORE - Memilih Masalah Terbaik
 * 
 * Scoring Formula:
 * score = (jumlah_keluhan * 0.4) + (emosi_negatif * 0.2) + 
 *         (mudah_otomatis * 0.2) + (potensi_uang * 0.2)
 */

class DecisionCore {
  constructor() {
    this.candidates = [];
  }

  // TF-IDF Vectorization (simplified)
  vectorize(text) {
    const words = text.split(' ');
    const vector = {};
    words.forEach(word => {
      vector[word] = (vector[word] || 0) + 1;
    });
    return vector;
  }

  // KMeans Clustering (simplified)
  cluster(problems) {
    console.log('   📊 Clustering masalah...');
    return problems;
  }

  // Analisis Sentimen
  analyzeSentiment(text) {
    const negativeWords = ['susah', 'ribet', 'gagal', 'error', 'bug', 'mati', 'rugi', 'bikin cape', 'mahal', 'rumit'];
    const positiveWords = ['mantap', 'bagus', 'senang', 'suka', 'easy', 'simple'];
    
    let score = 0;
    const lower = text.toLowerCase();
    
    negativeWords.forEach(w => { if(lower.includes(w)) score -= 1; });
    positiveWords.forEach(w => { if(lower.includes(w)) score += 1; });
    
    return score < 0 ? 'negative' : (score > 0 ? 'positive' : 'neutral');
  }

  // Estimasi kemudahan otomatisasi
  estimateAutomation(text) {
    const autoFriendly = ['auto', 'otomatis', 'system', 'app', 'tools', 'software', 'digital'];
    const manual = ['orang', 'manual', 'kerjain sendiri', 'pake orang'];
    
    let score = 0.5;
    const lower = text.toLowerCase();
    
    autoFriendly.forEach(w => { if(lower.includes(w)) score += 0.2; });
    manual.forEach(w => { if(lower.includes(w)) score -= 0.2; });
    
    return Math.max(0, Math.min(1, score));
  }

  // Estimasi potensi uang
  estimateMoneyPotential(text) {
    const highValue = ['jual', 'beli', 'uang', 'modal', 'bisnis', 'jualan', 'produk', 'harga'];
    const lowValue = ['cari', 'butuh', 'mau', ' cari gratisan', 'free'];
    
    let score = 0.5;
    const lower = text.toLowerCase();
    
    highValue.forEach(w => { if(lower.includes(w)) score += 0.2; });
    lowValue.forEach(w => { if(lower.includes(w)) score -= 0.2; });
    
    return Math.max(0, Math.min(1, score));
  }

  // Hitung Score
  calculateScore(problem) {
    const comments = problem.comments || problem.replies || problem.reviews || 10;
    const commentScore = Math.min(comments / 200, 1);

    const sentiment = this.analyzeSentiment(problem.text);
    const sentimentScore = sentiment === 'negative' ? 1 : (sentiment === 'neutral' ? 0.5 : 0.2);

    const autoScore = this.estimateAutomation(problem.text);
    const moneyScore = this.estimateMoneyPotential(problem.text);

    const score = (
      commentScore * 0.4 +
      sentimentScore * 0.2 +
      autoScore * 0.2 +
      moneyScore * 0.2
    );

    return {
      ...problem,
      scores: {
        comments: commentScore,
        sentiment: sentimentScore,
        automation: autoScore,
        money: moneyScore
      },
      totalScore: Math.round(score * 100) / 100
    };
  }

  async run(problems) {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║              🧠 DECISION CORE (OTAK)                    ║
╚═══════════════════════════════════════════════════════════╝
    `);

    const scored = problems.map(p => this.calculateScore(p));
    scored.sort((a, b) => b.totalScore - a.totalScore);

    console.log('\n📊 Top 5 Masalah:\n');
    scored.slice(0, 5).forEach((p, i) => {
      console.log(`   ${i+1}. ${p.text}`);
      console.log(`      Score: ${p.totalScore} | Comments: ${p.comments || p.replies || p.reviews || 0}`);
    });

    this.candidates = scored;
    return scored[0];
  }
}

export default DecisionCore;

// Run if called directly
if (process.argv[1] && process.argv[1].endsWith('decision/index.js')) {
  const decision = new DecisionCore();
  const testProblems = [
    { text: 'Susah cari freelancer terpercaya', comments: 150 },
    { text: 'Butuh tools auto posting IG', comments: 89 },
    { text: 'Toko online rumit setup', replies: 75 }
  ];
  decision.run(testProblems).then(best => {
    console.log('\n🧠 Best:', best);
    process.exit(0);
  });
}
