#!/usr/bin/env node
/**
 * 🛡️ IMMUNE SYSTEM - Anti Gila
 * Mencegah organisasi berjalan tidak terkendali
 */

class ImmuneSystem {
  constructor() {
    this.config = {
      max_iterasi_per_tugas: 10,
      timeout_keras_ms: 300000, // 5 menit
      batas_compute: {
        cpu: '1 core',
        ram: '512MB'
      },
      max_error_consecutive: 5,
      max_loop_detection: 100
    };
    
    this.counters = {
      iterasi: {},
      errors: {},
      loops: {}
    };
  }

  canContinue(taskId) {
    const current = this.counters.iterasi[taskId] || 0;
    
    if (current >= this.config.max_iterasi_per_tugas) {
      console.log(`   🛡️ MAX ITERASI: ${taskId} exceeded ${this.config.max_iterasi_per_tugas}`);
      return false;
    }
    
    this.counters.iterasi[taskId] = current + 1;
    return true;
  }

  checkTimeout(startTime, taskId) {
    const elapsed = Date.now() - startTime;
    
    if (elapsed > this.config.timeout_keras_ms) {
      console.log(`   🛡️ TIMEOUT: ${taskId} exceeded ${this.config.timeout_keras_ms}ms`);
      return false;
    }
    
    return true;
  }

  recordError(taskId) {
    const current = this.counters.errors[taskId] || 0;
    this.counters.errors[taskId] = current + 1;
    
    if (current + 1 >= this.config.max_error_consecutive) {
      console.log(`   🛡️ KILL: ${taskId} too many errors (${current + 1})`);
      return false;
    }
    
    return true;
  }

  detectLoop(taskId, state) {
    const key = `${taskId}_${JSON.stringify(state)}`;
    const current = this.counters.loops[key] || 0;
    
    this.counters.loops[key] = current + 1;
    
    if (current + 1 > this.config.max_loop_detection) {
      console.log(`   🛡️ LOOP DETECTED: ${taskId} repeating same state`);
      return false;
    }
    
    return true;
  }

  kill(taskId, reason) {
    console.log(`   💀 KILLING: ${taskId} - ${reason}`);
    
    delete this.counters.iterasi[taskId];
    
    return {
      killed: true,
      taskId,
      reason,
      timestamp: new Date().toISOString()
    };
  }

  reset(taskId) {
    this.counters.iterasi[taskId] = 0;
    this.counters.errors[taskId] = 0;
    console.log(`   🔄 Reset counters for: ${taskId}`);
  }

  healthCheck() {
    const errorTasks = Object.entries(this.counters.errors)
      .filter(([_, count]) => count >= 3)
      .map(([task, _]) => task);
    
    return {
      healthy: errorTasks.length === 0,
      warningTasks: errorTasks,
      totalErrors: Object.values(this.counters.errors).reduce((a, b) => a + b, 0)
    };
  }

  run() {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║              🛡️ IMMUNE SYSTEM (ANTI GILA)             ║
╚═══════════════════════════════════════════════════════════╝

⚙️  Config:
   - Max iterasi: ${this.config.max_iterasi_per_tugas}
   - Timeout: ${this.config.timeout_keras_ms / 1000}s
   - Max consecutive errors: ${this.config.max_error_consecutive}
   - Max loop detection: ${this.config.max_loop_detection}
    `);

    const health = this.healthCheck();
    console.log('\n💚 Health:', health);
    
    return this.config;
  }
}

export default ImmuneSystem;

// Run if called directly
if (process.argv[1] && process.argv[1].endsWith('immune/index.js')) {
  const immune = new ImmuneSystem();
  immune.run();
  process.exit(0);
}
