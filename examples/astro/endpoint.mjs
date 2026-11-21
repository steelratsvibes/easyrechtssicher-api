import { respond } from '../shared/client.mjs';
export const prerender = false;
// Requires an Astro server adapter with a Node runtime.
export function GET() { return respond(process.env.EASYRECHTSSICHER_MODE || 'stack'); }
