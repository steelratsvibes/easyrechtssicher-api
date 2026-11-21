import { KEY_ERROR, run } from '../shared/client.mjs';
try { console.log(JSON.stringify(await run(process.argv[2] || 'stack'))); }
catch (error) {
  console.error(error.message === KEY_ERROR ? KEY_ERROR : 'Example failed');
  process.exitCode = 1;
}
