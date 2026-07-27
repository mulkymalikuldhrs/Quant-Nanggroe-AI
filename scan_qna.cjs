const fs = require('fs'), path = require('path');
function walk(dir) {
  const out = [];
  try {
    for (const f of fs.readdirSync(dir)) {
      if (f.startsWith('.') || f === 'node_modules' || f === '__pycache__' || f === 'venv' || f === '.venv') continue;
      const full = path.join(dir, f);
      try {
        const stat = fs.statSync(full);
        if (stat.isDirectory()) out.push(...walk(full));
        else out.push(full);
      } catch(e) {}
    }
  } catch(e) {}
  return out;
}
const all = walk('D:/repositories/Quant-Nanggroe-AI-worktree');
console.log('TOTAL:', all.length);
const exts = {};
all.forEach(f => { const e = path.extname(f) || '(no ext)'; exts[e] = (exts[e]||0)+1; });
Object.entries(exts).sort((a,b) => b[1]-a[1]).forEach(([e,c]) => console.log(e+': '+c));
console.log('---FILES---');
all.forEach(f => console.log(f));
