// Private settings created by the local launcher. Never served by the website.
import { readFileSync, existsSync } from 'node:fs';
const file = new URL('../.env.local.json', import.meta.url);
if (existsSync(file)) {
  const settings = JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  for (const [key, value] of Object.entries(settings)) {
    if (/^(BB_|TWILIO_)/.test(key) || key === 'PORT') {
      process.env[key] ??= String(value);
    }
  }
}
