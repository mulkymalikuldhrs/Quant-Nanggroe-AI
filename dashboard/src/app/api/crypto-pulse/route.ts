import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { existsSync } from "fs";
import { join } from "path";

const DATA_DIR = (() => {
  const candidates = [
    join(process.cwd(), "..", "data", "crypto", "crypto_pulse.json"),
    join(process.cwd(), "..", "..", "data", "crypto", "crypto_pulse.json"),
  ];
  return candidates.find(p => existsSync(p)) || candidates[0];
})();

export async function GET() {
  try {
    if (existsSync(DATA_DIR)) {
      const raw = await readFile(DATA_DIR, "utf-8");
      return NextResponse.json(JSON.parse(raw));
    }
    return NextResponse.json(
      { error: "Daemon data not available. Run crypto_pulse daemon first.", data: null },
      { status: 503 }
    );
  } catch {
    return NextResponse.json(
      { error: "Failed to read crypto pulse data", data: null },
      { status: 500 }
    );
  }
}
