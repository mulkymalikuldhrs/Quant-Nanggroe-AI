import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Server-side middleware: injects API key into outgoing requests to the
 * FastAPI backend. The key is NEVER exposed to client-side JS because
 * middleware runs on the server only (not bundled into the browser).
 *
 * Environment: QNA_API_KEY (server-side only, NOT NEXT_PUBLIC).
 */
export function middleware(request: NextRequest) {
  const apiKey = process.env.QNA_API_KEY;
  const url = request.nextUrl;

  // Only inject for API proxy routes or direct backend calls
  if (url.pathname.startsWith("/api/") && apiKey) {
    const requestHeaders = new Headers(request.headers);
    if (!requestHeaders.has("Authorization")) {
      requestHeaders.set("Authorization", `ApiKey ${apiKey}`);
    }
    return NextResponse.next({ request: { headers: requestHeaders } });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/:path*"],
};
