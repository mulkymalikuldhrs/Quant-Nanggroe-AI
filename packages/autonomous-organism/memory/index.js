#!/usr/bin/env node
/**
 * 📚 MEMORY ENGINE - Ingatan Organisme
 * Mempelajari dari kesalahan dan keberhasilan
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const LOG_FILE = path.join(process.cwd(), 'memory', 'life_log.json');

class MemoryEngine {
  constructor() {
    this.logs = [];
    this.load();
  }

  load() {
    if (fs.existsSync(LOG_FILE)) {
      try {
        this.logs = JSON.parse(fs.readFileSync(LOG_FILE, 'utf8'));
      } catch(e) {
        this.logs = [];
      }
    }
  }

  save() {
    const dir = path.dirname(LOG_FILE);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(LOG_FILE, JSON.stringify(this.logs, null, 2));
  }

  // Catat hasil
  log(type, name, result, reason) {
    const entry = {
      id: this.logs.length + 1,
      type, // 'PRODUCT', 'AGENT', 'CAMPAIGN'
      name,
      result, // 'SUCCESS', 'FAILED', 'PIVOT'
      reason,
      date: new Date().toISOString()
    };
    
    this.logs.push(entry);
    this.save();
    
    console.log(`   📝 Logged: ${type} - ${name} = ${result}`);
    return entry;
  }

  // Analisa pola gagal
  analyzeFailures() {
    const failures = this.logs.filter(l => l.result === 'FAILED');
    
    const reasons = {};
    failures.forEach(f => {
      reasons[f.reason] = (reasons[f.reason] || 0) + 1;
    });
    
    const topReasons = Object.entries(reasons)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    console.log('\n💀 Top Kegagalan:');
    topReasons.forEach(([reason, count]) => {
      console.log(`   - ${reason}: ${count}x`);
    });
    
    return topReasons;
  }

  // Analisa pola sukses
  analyzeSuccess() {
    const successes = this.logs.filter(l => l.result === 'SUCCESS');
    
    const types = {};
    successes.forEach(s => {
      types[s.type] = (types[s.type] || 0) + 1;
    });
    
    console.log('\n✅ Jenis Sukses:');
    Object.entries(types).forEach(([type, count]) => {
      console.log(`   - ${type}: ${count}x`);
    });
    
    return types;
  }

  // Mingguan review
  weeklyReview() {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║              📚 MEMORY ENGINE - WEEKLY REVIEW          ║
╚═══════════════════════════════════════════════════════════╝
    `);
    
    const failures = this.analyzeFailures();
    const successes = this.analyzeSuccess();
    
    console.log('\n📊 Rekomendasi:');
    
    if (failures.length > 0) {
      console.log(`   💡 Hindari: ${failures[0][0]}`);
    }
    
    if (Object.keys(successes).length > 0) {
      console.log(`   💡 Fokus: ${Object.keys(successes)[0]}`);
    }
    
    return { failures, successes };
  }

  run() {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║              📚 MEMORY ENGINE (INGATAN)               ║
╚═══════════════════════════════════════════════════════════╝
    `);
    
    console.log(`   📊 Total logs: ${this.logs.length}`);
    
    return this.logs;
  }
}

export default MemoryEngine;

// Run if called directly
if (process.argv[1] && process.argv[1].endsWith('memory/index.js')) {
  const memory = new MemoryEngine();
  memory.run();
  
  memory.log('PRODUCT', 'AutoPost IG', 'FAILED', 'No user interest');
  memory.log('PRODUCT', 'Chat Bot', 'SUCCESS', 'High demand');
  memory.log('AGENT', 'Content Writer', 'FAILED', 'Cost too high');
  
  memory.weeklyReview();
  
  process.exit(0);
}
