import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const envPath = path.resolve(__dirname, "..", ".env");

function detectLocalIp() {
  const ifaces = os.networkInterfaces();
  const candidates = [];

  for (const [name, list] of Object.entries(ifaces)) {
    if (/^(docker|br-|veth|virbr|tun)/i.test(name)) continue;
    for (const iface of list || []) {
      if (iface.family === "IPv4" && !iface.internal) {
        candidates.push({ name, address: iface.address });
      }
    }
  }

  // Prioritize Wi-Fi or Ethernet interfaces
  const preferred = candidates.find(c => /^(wl|en|eth)/i.test(c.name));
  if (preferred) return preferred.address;
  if (candidates.length > 0) return candidates[0].address;

  return "localhost";
}

const detectedIp = detectLocalIp();
const apiUrl = `http://${detectedIp}:8000/api/v1`;

let content = "";
if (fs.existsSync(envPath)) {
  content = fs.readFileSync(envPath, "utf-8");
  if (/^EXPO_PUBLIC_API_URL=.*$/m.test(content)) {
    content = content.replace(/^EXPO_PUBLIC_API_URL=.*$/m, `EXPO_PUBLIC_API_URL=${apiUrl}`);
  } else {
    content += `\nEXPO_PUBLIC_API_URL=${apiUrl}\n`;
  }
} else {
  content = `# Penny Mobile Local Environment\nEXPO_PUBLIC_API_URL=${apiUrl}\n`;
}

fs.writeFileSync(envPath, content.trim() + "\n");
console.log(`✔ Configured EXPO_PUBLIC_API_URL=${apiUrl} in frontend/.env`);
