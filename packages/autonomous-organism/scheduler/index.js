#!/usr/bin/env node
/**
 * ❤️ SCHEDULER - Jantung Organisme
 * Siklus: Per jam, Harian, Mingguan, Bulanan
 */

class Scheduler {
  constructor() {
    this.cycles = {
      hourly: 0,
      daily: 0,
      weekly: 0,
      monthly: 0
    };
    
    this.lastRun = {
      hourly: null,
      daily: null,
      weekly: null,
      monthly: null
    };
  }

  shouldRun(cycle, intervalMs) {
    const last = this.lastRun[cycle];
    if (!last) return true;
    return Date.now() - last > intervalMs;
  }

  async runHourly(callback) {
    if (this.shouldRun('hourly', 3600000)) {
      console.log('\n⏰ [HOURLY CYCLE]');
      await callback();
      this.lastRun.hourly = Date.now();
      this.cycles.hourly++;
    }
  }

  async runDaily(callback) {
    if (this.shouldRun('daily', 86400000)) {
      console.log('\n🌅 [DAILY CYCLE]');
      await callback();
      this.lastRun.daily = Date.now();
      this.cycles.daily++;
    }
  }

  async runWeekly(callback) {
    if (this.shouldRun('weekly', 604800000)) {
      console.log('\n📅 [WEEKLY CYCLE]');
      await callback();
      this.lastRun.weekly = Date.now();
      this.cycles.weekly++;
    }
  }

  async runMonthly(callback) {
    if (this.shouldRun('monthly', 2592000000)) {
      console.log('\n🗓️ [MONTHLY CYCLE]');
      await callback();
      this.lastRun.monthly = Date.now();
      this.cycles.monthly++;
    }
  }

  async hourlyAction() {
    console.log('   👁️ Scan masalah baru');
    console.log('   📊 Update analytics');
  }

  async dailyAction() {
    console.log('   🏭 Bangun/upgrade produk');
    console.log('   📢 Run campaign');
    console.log('   💰 Collect revenue');
  }

  async weeklyAction() {
    console.log('   💀 Bunuh yang gagal');
    console.log('   📊 Analisa mingguan');
    console.log('   🔄 Update strategi');
  }

  async monthlyAction() {
    console.log('   🎯 Evaluasi spesies');
    console.log('   💰 Monthly revenue report');
    console.log('   🧬 Spawn agent baru jika perlu');
  }

  async start(organisme) {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║              ❤️ SCHEDULER (JANTUNG)                   ║
╚═══════════════════════════════════════════════════════════╝

⏰ Hourly:  Scan masalah
🌅 Daily:   Bangun produk
📅 Weekly:  Bunuh gagal
🗓️ Monthly: Evaluasi spesies
    `);

    await this.runHourly(() => this.hourlyAction());
    await this.runDaily(() => this.dailyAction());
    await this.runWeekly(() => this.weeklyAction());
    await this.runMonthly(() => this.monthlyAction());

    console.log('\n📊 Cycle Stats:', this.cycles);
    
    return this.cycles;
  }
}

export default Scheduler;
