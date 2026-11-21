import { respond } from '../shared/client.mjs';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
// Server configuration, never a browser-supplied key or upstream URL.
export function GET() { return respond(process.env.EASYRECHTSSICHER_MODE || 'stack'); }
