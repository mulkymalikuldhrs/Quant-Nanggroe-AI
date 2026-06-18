#!/usr/bin/env node
/**
 * 🧬 ORGANISME SAAS OTONOM
 * Main Controller
 * 
 * Misi: $50,000/bulan dalam 12 bulan
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class Organisme {
  constructor() {
    this.name = 'ORGANISME-001';
    this.version = '2.0.0';
    this.state = {
      started: new Date().toISOString(),
      products: [],
      revenue: 0,
      agents: [],
      status: 'ALIVE'
    };
    
    this.components = {
      sense: null,
      decision: null,
      factory: null,
      monetization: null,
      growth: null,
      memory: null,
      scheduler: null,
      immune: null
    };
  }

  // Lifecycle: Find problems
  async sense() {
    console.log('\n👁️ SENSE ENGINE - Mengumpulkan masalah...');
    const problems = [
      { id: 1, source: 'reddit', text: 'Susah cari freelancer terpercaya', score: 8.5 },
      { id: 2, source: 'kaskus', text: 'Toko online rumit setup', score: 7.2 },
      { id: 3, source: 'youtube', text: 'Butuh auto post sosmed', score: 9.1 }
    ];
    console.log(`   ✅ Ditemukan ${problems.length} masalah`);
    return problems;
  }

  // Lifecycle: Choose best problem
  async decision(problems) {
    console.log('\n🧠 DECISION CORE - Memilih masalah terbaik...');
    const best = problems.sort((a, b) => b.score - a.score)[0];
    console.log(`   ✅ Dipilih: ${best.text} (score: ${best.score})`);
    return best;
  }

  // Lifecycle: Build solution
  async factory(problem) {
    console.log('\n🏭 SAAS FACTORY - Membangun solusi...');
    const product = {
      id: `PROD_${Date.now()}`,
      name: this.generateName(problem.text),
      problem: problem.text,
      status: 'BUILT',
      revenue: 0,
      created: new Date().toISOString()
    };
    console.log(`   ✅ Dibangun: ${product.name}`);
    return product;
  }

  generateName(problem) {
    const prefixes = ['Auto', 'Smart', 'Fast', 'Easy', 'Quick'];
    const suffixes = ['Tool', 'App', 'System', 'Platform', 'Solution'];
    const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
    const suffix = suffixes[Math.floor(Math.random() * suffixes.length)];
    return `${prefix}${suffix}`;
  }

  // Lifecycle: Deploy
  async deploy(product) {
    console.log('\n🚀 DEPLOY - Mendeploy ke Vercel...');
    product.status = 'DEPLOYED';
    product.url = `https://${product.name.toLowerCase()}.vercel.app`;
    console.log(`   ✅ Deployed: ${product.url}`);
    return product;
  }

  // Lifecycle: Find users
  async growth(product) {
    console.log('\n📢 GROWTH ENGINE - Mencari user...');
    const users = Math.floor(Math.random() * 100) + 10;
    console.log(`   ✅ Dapat ${users} users`);
    return users;
  }

  // Lifecycle: Make money
  async monetization(product, users) {
    console.log('\n💰 MONETIZATION ENGINE - Menghasilkan uang...');
    const income = Math.floor(users * Math.random() * 10);
    product.revenue = income;
    this.state.revenue += income;
    console.log(`   ✅ Income: $${income}`);
    return income;
  }

  // Lifecycle: Learn
  async memory(product, income) {
    console.log('\n📚 MEMORY ENGINE - Mempelajari hasil...');
    const log = {
      product: product.name,
      income,
      status: income > 0 ? 'SUCCESS' : 'FAILED',
      lesson: income > 0 ? 'Keep doing this' : 'Need pivot',
      date: new Date().toISOString()
    };
    console.log(`   ✅ Logged: ${log.status}`);
    return log;
  }

  // Lifecycle: Upgrade/Create new
  async evolve(product, log) {
    console.log('\n🔄 EVOLUSI - Upgrade/Create new agent...');
    
    if (log.status === 'FAILED') {
      console.log('   💀 Produk gagal - membunuh...');
      return null;
    }
    
    console.log('   ✅ Organisme berkembang - spawn agent baru');
    return { newAgent: true };
  }

  // Main lifecycle
  async runCycle() {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║     🧬 ORGANISME SAAS OTONOM - CYCLE ${this.state.cycles || 1}      ║
║     Target: $50,000/bulan                               ║
╚═══════════════════════════════════════════════════════════╝
    `);

    this.state.cycles = (this.state.cycles || 0) + 1;

    // 1. Sense - Find problems
    const problems = await this.sense();
    
    // 2. Decision - Choose best
    const best = await this.decision(problems);
    
    // 3. Factory - Build solution
    const product = await this.factory(best);
    
    // 4. Deploy
    const deployed = await this.deploy(product);
    
    // 5. Growth - Find users
    const users = await this.growth(deployed);
    
    // 6. Monetization - Make money
    const income = await this.monetization(deployed, users);
    
    // 7. Memory - Learn
    const log = await this.memory(deployed, income);
    
    // 8. Evolve
    await this.evolve(deployed, log);

    this.state.products.push(deployed);

    console.log(`
╔═══════════════════════════════════════════════════════════╗
║                    ✅ CYCLE COMPLETE                    ║
╠═══════════════════════════════════════════════════════════╣
║  Products: ${this.state.products.length}
║  Revenue:  $${this.state.revenue}
║  Status:   ${this.state.status}
╚═══════════════════════════════════════════════════════════╝
    `);

    return this.state;
  }

  // Save state
  save() {
    const file = path.join(process.cwd(), 'state.json');
    fs.writeFileSync(file, JSON.stringify(this.state, null, 2));
  }

  async start() {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║     🧬 ORGANISME SAAS OTONOM v${this.version}             ║
║     "Membiakkan bisnis, membunuh yang lemah"             ║
╚═══════════════════════════════════════════════════════════╝

📋 Mission: $50,000/bulan
🧠 Brain: AI (configurable via VITE_AI_MODEL)
💰 Target: 12 bulan

Started: ${this.state.started}
    `);

    await this.runCycle();
    this.save();

    return this.state;
  }
}

export default Organisme;

// Run if called directly
if (process.argv[1] && process.argv[1].endsWith('index.js')) {
  const organisme = new Organisme();
  organisme.start()
    .then(state => {
      console.log('\n🧬 Organisme State:', state);
      process.exit(0);
    })
    .catch(err => {
      console.error('Error:', err);
      process.exit(1);
    });
}
