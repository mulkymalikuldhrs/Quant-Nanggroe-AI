#!/usr/bin/env node
/**
 * 👁️ SENSE ENGINE - Mengumpulkan Masalah Manusia
 */

const SOURCES = {
  reddit: ['r/indonesia', 'r/startups', 'r/sideproject', 'r/smallbusiness'],
  kaskus: ['Forum Bisnis', 'Forum Tech', 'Forum Karir'],
  quora: ['indonesian-quora'],
  youtube: ['Komentar video trending Indonesia'],
  marketplace: ['Shopee reviews', 'Tokopedia reviews'],
  telegram: ['Public groups Indonesia']
};

class SenseEngine {
  constructor() {
    this.db = [];
  }

  async scrapeReddit() {
    console.log('   📱 Scraping Reddit...');
    // Simulasi - nanti pakai Playwright/Puppeteer
    return [
      { source: 'reddit', text: 'Susah cari freelancer terpercaya', comments: 150, sentiment: 'negative' },
      { source: 'reddit', text: 'Butuh tools auto posting IG', comments: 89, sentiment: 'negative' },
      { source: 'reddit', text: 'Cara buat toko online mudah?', comments: 200, sentiment: 'neutral' }
    ];
  }

  async scrapeKaskus() {
    console.log('   💬 Scraping Kaskus...');
    return [
      { source: 'kaskus', text: 'Toko online rumit setup', replies: 75, sentiment: 'negative' },
      { source: 'kaskus', text: 'Mau jualan tapi ga bisa design', replies: 45, sentiment: 'negative' }
    ];
  }

  async scrapeMarketplace() {
    console.log('   🛒 Scraping Marketplace reviews...');
    return [
      { source: 'shopee', text: 'Aplikasi kasir yang mudah', reviews: 300, sentiment: 'negative' },
      { source: 'tokopedia', text: 'Butuh auto reply chat', reviews: 120, sentiment: 'negative' }
    ];
  }

  cleanText(text) {
    return text.toLowerCase()
      .replace(/https?:\/\/\S+/g, '')
      .replace(/@\w+/g, '')
      .replace(/[^\w\s]/g, '')
      .trim();
  }

  async run() {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║              👁️ SENSE ENGINE (INDRA)                    ║
╚═══════════════════════════════════════════════════════════╝
    `);

    const [reddit, kaskus, marketplace] = await Promise.all([
      this.scrapeReddit(),
      this.scrapeKaskus(),
      this.scrapeMarketplace()
    ]);

    const allProblems = [...reddit, ...kaskus, ...marketplace]
      .map(p => ({
        ...p,
        text_clean: this.cleanText(p.text)
      }))
      .filter((v, i, a) => a.findIndex(t => t.text_clean === v.text_clean) === i);

    console.log(`\n✅ Total masalah ditemukan: ${allProblems.length}`);
    this.db = allProblems;
    return allProblems;
  }
}

export default SenseEngine;

// Run if called directly
if (process.argv[1] && process.argv[1].endsWith('sense/index.js')) {
  const sense = new SenseEngine();
  sense.run().then(problems => {
    console.log('\n👁️ Problems:', problems);
    process.exit(0);
  });
}
