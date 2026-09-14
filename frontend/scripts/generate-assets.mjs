import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const assetsDir = path.join(rootDir, "assets");

if (!fs.existsSync(assetsDir)) {
  fs.mkdirSync(assetsDir, { recursive: true });
}

// 1. Master Brand SVG (1024x1024) for App Store & Standard Launcher
function createMasterIconSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="1024" height="1024" viewBox="0 0 1024 1024" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Background Gradient -->
    <radialGradient id="bgGrad" cx="50%" cy="45%" r="65%" fx="50%" fy="45%">
      <stop offset="0%" stop-color="#161E2E" />
      <stop offset="60%" stop-color="#0B0F19" />
      <stop offset="100%" stop-color="#06090E" />
    </radialGradient>

    <!-- Outer Glow -->
    <radialGradient id="auraGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#D97706" stop-opacity="0.25" />
      <stop offset="60%" stop-color="#B45309" stop-opacity="0.08" />
      <stop offset="100%" stop-color="#0B0F19" stop-opacity="0" />
    </radialGradient>

    <!-- Coin Rim Gradient -->
    <linearGradient id="coinRim" x1="200" y1="200" x2="824" y2="824" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#FDE68A" />
      <stop offset="25%" stop-color="#F59E0B" />
      <stop offset="70%" stop-color="#D97706" />
      <stop offset="100%" stop-color="#78350F" />
    </linearGradient>

    <!-- Coin Face Gradient -->
    <radialGradient id="coinFace" cx="45%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#2D2115" />
      <stop offset="50%" stop-color="#191B24" />
      <stop offset="100%" stop-color="#0F121C" />
    </radialGradient>

    <!-- Monogram Metallic Gradient -->
    <linearGradient id="monogramGrad" x1="420" y1="340" x2="600" y2="680" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#FFFBEB" />
      <stop offset="30%" stop-color="#FDE68A" />
      <stop offset="70%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#B45309" />
    </linearGradient>

    <!-- Trajectory Glowing Beam -->
    <linearGradient id="trajectoryGrad" x1="160" y1="680" x2="880" y2="240" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#D97706" stop-opacity="0.2" />
      <stop offset="40%" stop-color="#F59E0B" />
      <stop offset="85%" stop-color="#FDE68A" />
      <stop offset="100%" stop-color="#FFFFFF" />
    </linearGradient>

    <!-- Filter for trajectory glow -->
    <filter id="glowFilter" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="12" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Background Base -->
  <rect width="1024" height="1024" rx="224" fill="url(#bgGrad)" />

  <!-- Ambient Coin Glow -->
  <circle cx="512" cy="512" r="380" fill="url(#auraGlow)" />

  <!-- Financial Radar & Trajectory Calibration Ring -->
  <circle cx="512" cy="512" r="380" stroke="#1E293B" stroke-width="2" stroke-dasharray="8 8" />
  <circle cx="512" cy="512" r="340" stroke="#2D3748" stroke-width="1.5" stroke-opacity="0.6" />
  <line x1="512" y1="110" x2="512" y2="150" stroke="#F59E0B" stroke-width="2" stroke-opacity="0.7" />
  <line x1="512" y1="874" x2="512" y2="914" stroke="#F59E0B" stroke-width="2" stroke-opacity="0.7" />
  <line x1="110" y1="512" x2="150" y2="512" stroke="#F59E0B" stroke-width="2" stroke-opacity="0.7" />
  <line x1="874" y1="512" x2="914" y2="512" stroke="#F59E0B" stroke-width="2" stroke-opacity="0.7" />

  <!-- Data Coordinates Accent Dots -->
  <circle cx="820" cy="300" r="4" fill="#38BDF8" />
  <circle cx="860" cy="360" r="3" fill="#10B981" />
  <circle cx="210" cy="420" r="3" fill="#64748B" />
  <circle cx="260" cy="620" r="4" fill="#F59E0B" />

  <!-- Main Coin Outer Rim -->
  <circle cx="512" cy="512" r="250" fill="url(#coinRim)" />
  <circle cx="512" cy="512" r="236" fill="url(#coinFace)" stroke="#F59E0B" stroke-width="2" stroke-opacity="0.4" />

  <!-- Coin Reeding / Inner Accent Rim -->
  <circle cx="512" cy="512" r="218" stroke="#D97706" stroke-width="2" stroke-dasharray="4 4" stroke-opacity="0.6" />
  <circle cx="512" cy="512" r="206" stroke="#FDE68A" stroke-width="1.5" stroke-opacity="0.25" />

  <!-- Central 'P' Stylized Monogram (Double-Rib Architecture) -->
  <!-- Outer P outline -->
  <path d="M436 340 H548 C606 340 650 380 650 438 C650 496 606 536 548 536 H496 V684 H436 V340 Z" fill="url(#monogramGrad)" />
  <!-- Inner P cutout -->
  <path d="M496 400 H544 C572 400 592 416 592 438 C592 460 572 476 544 476 H496 V400 Z" fill="#141824" />
  <!-- Architectural Coin Notches / Crossbar Ticks -->
  <rect x="410" y="426" width="30" height="8" rx="2" fill="#FDE68A" />
  <rect x="410" y="478" width="30" height="8" rx="2" fill="#FDE68A" />
  <rect x="520" y="326" width="8" height="18" rx="2" fill="#FDE68A" />
  <rect x="556" y="326" width="8" height="18" rx="2" fill="#FDE68A" />

  <!-- Ascending Forward Trajectory Curve with Glow -->
  <!-- Glow underlay -->
  <path d="M160 690 C 290 690, 360 630, 470 545 C 570 465, 710 340, 830 240" 
        stroke="#F59E0B" stroke-width="18" stroke-linecap="round" fill="none" opacity="0.3" filter="url(#glowFilter)" />
  <!-- Secondary inner trajectory guide line -->
  <path d="M220 730 C 330 730, 420 660, 520 575 C 620 495, 740 370, 860 270" 
        stroke="#FDE68A" stroke-width="3" stroke-linecap="round" stroke-dasharray="6 8" fill="none" opacity="0.6" />
  <!-- Main sharp trajectory vector -->
  <path d="M160 690 C 290 690, 360 630, 470 545 C 570 465, 710 340, 830 240" 
        stroke="url(#trajectoryGrad)" stroke-width="10" stroke-linecap="round" fill="none" />
  <!-- Dynamic Ascending Arrow Head -->
  <polygon points="852,222 812,246 830,264" fill="#FFFFFF" />
  <polygon points="852,222 822,238 834,250" fill="#FDE68A" />

  <!-- Trajectory Point Highlights -->
  <circle cx="830" cy="240" r="6" fill="#FFFFFF" />
</svg>`;
}

// 2. Android Adaptive Icon Foreground (432x432, transparent background)
// Safe zone is central 288px (margin = 72px)
function createAdaptiveForegroundSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="432" height="432" viewBox="0 0 432 432" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="afCoinRim" x1="120" y1="120" x2="312" y2="312" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#FDE68A" />
      <stop offset="35%" stop-color="#F59E0B" />
      <stop offset="75%" stop-color="#D97706" />
      <stop offset="100%" stop-color="#78350F" />
    </linearGradient>

    <radialGradient id="afCoinFace" cx="45%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#2D2115" />
      <stop offset="50%" stop-color="#191B24" />
      <stop offset="100%" stop-color="#0F121C" />
    </radialGradient>

    <linearGradient id="afMonogram" x1="180" y1="150" x2="250" y2="280" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#FFFBEB" />
      <stop offset="30%" stop-color="#FDE68A" />
      <stop offset="70%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#B45309" />
    </linearGradient>

    <linearGradient id="afTrajectory" x1="70" y1="285" x2="360" y2="105" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#D97706" stop-opacity="0.3" />
      <stop offset="40%" stop-color="#F59E0B" />
      <stop offset="85%" stop-color="#FDE68A" />
      <stop offset="100%" stop-color="#FFFFFF" />
    </linearGradient>

    <filter id="afGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Group centered in 432x432 -->
  <g transform="translate(0, 0)">
    <!-- Radar ring -->
    <circle cx="216" cy="216" r="144" stroke="#2D3748" stroke-width="1" stroke-dasharray="4 4" stroke-opacity="0.5" />
    
    <!-- Coin Outer Rim (Radius 98px within 144px safe zone) -->
    <circle cx="216" cy="216" r="96" fill="url(#afCoinRim)" />
    <circle cx="216" cy="216" r="90" fill="url(#afCoinFace)" stroke="#F59E0B" stroke-width="1" stroke-opacity="0.5" />
    <circle cx="216" cy="216" r="82" stroke="#D97706" stroke-width="1" stroke-dasharray="3 3" stroke-opacity="0.6" />

    <!-- 'P' Monogram -->
    <path d="M186 150 H230 C254 150 272 166 272 190 C272 214 254 230 230 230 H210 V282 H186 V150 Z" fill="url(#afMonogram)" />
    <path d="M210 174 H228 C238 174 248 181 248 190 C248 199 238 206 228 206 H210 V174 Z" fill="#141824" />
    <rect x="176" y="185" width="12" height="4" rx="1" fill="#FDE68A" />
    <rect x="176" y="206" width="12" height="4" rx="1" fill="#FDE68A" />
    <rect x="220" y="144" width="4" height="8" rx="1" fill="#FDE68A" />
    <rect x="234" y="144" width="4" height="8" rx="1" fill="#FDE68A" />

    <!-- Trajectory Sweep -->
    <path d="M78 288 C 130 288, 160 262, 205 228 C 248 195, 305 145, 350 106" 
          stroke="#F59E0B" stroke-width="8" stroke-linecap="round" fill="none" opacity="0.3" filter="url(#afGlow)" />
    <path d="M78 288 C 130 288, 160 262, 205 228 C 248 195, 305 145, 350 106" 
          stroke="url(#afTrajectory)" stroke-width="4.5" stroke-linecap="round" fill="none" />
    <polygon points="358,98 340,110 348,118" fill="#FFFFFF" />
  </g>
</svg>`;
}

// 3. Android Adaptive Icon Background (432x432)
function createAdaptiveBackgroundSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="432" height="432" viewBox="0 0 432 432" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="abGrad" cx="50%" cy="45%" r="65%">
      <stop offset="0%" stop-color="#1A2234" />
      <stop offset="60%" stop-color="#0B0F19" />
      <stop offset="100%" stop-color="#05080E" />
    </radialGradient>
  </defs>
  <rect width="432" height="432" fill="url(#abGrad)" />
</svg>`;
}

// 4. Android Adaptive Icon Monochrome (432x432 for Material You dynamic theming)
function createAdaptiveMonochromeSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="432" height="432" viewBox="0 0 432 432" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Group centered in 432x432 -->
  <g transform="translate(0, 0)">
    <!-- Radar ring -->
    <circle cx="216" cy="216" r="144" stroke="#FFFFFF" stroke-width="1.5" stroke-dasharray="4 4" stroke-opacity="0.4" />
    
    <!-- Coin Ring Silhouette -->
    <circle cx="216" cy="216" r="96" stroke="#FFFFFF" stroke-width="6" fill="none" />
    <circle cx="216" cy="216" r="84" stroke="#FFFFFF" stroke-width="1" stroke-dasharray="3 3" stroke-opacity="0.6" fill="none" />

    <!-- 'P' Monogram Silhouette -->
    <path d="M186 150 H230 C254 150 272 166 272 190 C272 214 254 230 230 230 H210 V282 H186 V150 Z" fill="#FFFFFF" />
    <!-- Cutout inside P -->
    <path d="M210 174 H228 C238 174 248 181 248 190 C248 199 238 206 228 206 H210 V174 Z" fill="#000000" />
    <rect x="176" y="185" width="12" height="4" rx="1" fill="#FFFFFF" />
    <rect x="176" y="206" width="12" height="4" rx="1" fill="#FFFFFF" />

    <!-- Trajectory Sweep Silhouette -->
    <path d="M78 288 C 130 288, 160 262, 205 228 C 248 195, 305 145, 350 106" 
          stroke="#FFFFFF" stroke-width="5" stroke-linecap="round" fill="none" />
    <polygon points="358,98 340,110 348,118" fill="#FFFFFF" />
  </g>
</svg>`;
}

// 5. Favicon SVG (64x64)
function createFaviconSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="favCoin" x1="12" y1="12" x2="52" y2="52">
      <stop offset="0%" stop-color="#FDE68A" />
      <stop offset="50%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#B45309" />
    </linearGradient>
    <linearGradient id="favTraj" x1="10" y1="46" x2="56" y2="14">
      <stop offset="0%" stop-color="#F59E0B" />
      <stop offset="100%" stop-color="#FFFFFF" />
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" fill="#0B0F19" />
  <!-- Coin rim -->
  <circle cx="32" cy="32" r="18" fill="url(#favCoin)" />
  <circle cx="32" cy="32" r="14" fill="#141824" />
  <!-- Monogram P -->
  <path d="M26 21 H33 C37 21 40 23.5 40 27 C40 30.5 37 33 33 33 H30 V42 H26 V21 Z" fill="#FDE68A" />
  <path d="M30 25 H33 C34.5 25 36 26 36 27 C36 28 34.5 29 33 29 H30 V25 Z" fill="#141824" />
  <!-- Trajectory curve -->
  <path d="M8 46 C 18 46, 26 40, 34 32 C 40 26, 48 18, 56 12" stroke="url(#favTraj)" stroke-width="2.5" stroke-linecap="round" fill="none" />
  <polygon points="58,10 52,14 55,17" fill="#FFFFFF" />
</svg>`;
}

async function main() {
  console.log("🪙 Starting Penny Asset Generation Suite...");

  const tempDir = path.join(assetsDir, ".temp");
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
  }

  try {
    // 1. Write SVGs to temporary directory
    const masterSvgPath = path.join(tempDir, "master-icon.svg");
    const afSvgPath = path.join(tempDir, "adaptive-foreground.svg");
    const abSvgPath = path.join(tempDir, "adaptive-background.svg");
    const amSvgPath = path.join(tempDir, "adaptive-monochrome.svg");
    const favSvgPath = path.join(tempDir, "favicon.svg");

    fs.writeFileSync(masterSvgPath, createMasterIconSvg());
    fs.writeFileSync(afSvgPath, createAdaptiveForegroundSvg());
    fs.writeFileSync(abSvgPath, createAdaptiveBackgroundSvg());
    fs.writeFileSync(amSvgPath, createAdaptiveMonochromeSvg());
    fs.writeFileSync(favSvgPath, createFaviconSvg());

    console.log("✔ Vector SVG source templates written.");

    // 2. Render PNGs via ImageMagick
    console.log("Rendering 1024x1024 app icon...");
    execSync(`magick "${masterSvgPath}" -resize 1024x1024 -quality 100 "${path.join(assetsDir, "icon.png")}"`);

    console.log("Rendering 432x432 Android adaptive foreground...");
    execSync(`magick -background none "${afSvgPath}" -resize 432x432 "${path.join(assetsDir, "android-icon-foreground.png")}"`);

    console.log("Rendering 432x432 Android adaptive background...");
    execSync(`magick "${abSvgPath}" -resize 432x432 "${path.join(assetsDir, "android-icon-background.png")}"`);

    console.log("Rendering 432x432 Android adaptive monochrome...");
    execSync(`magick -background none "${amSvgPath}" -resize 432x432 "${path.join(assetsDir, "android-icon-monochrome.png")}"`);

    console.log("Rendering 48x48 web favicon...");
    execSync(`magick -background none "${favSvgPath}" -resize 48x48 "${path.join(assetsDir, "favicon.png")}"`);

    // 3. Process Cinematic Splash Artwork
    const brainDir = "/home/varun/.gemini/antigravity-cli/brain/51dbcfa4-4bc9-465c-a4b1-487132f9b17e";
    const splashCandidates = fs.readdirSync(brainDir).filter(f => f.startsWith("penny_splash_artwork_") && f.endsWith(".jpg"));
    
    if (splashCandidates.length > 0) {
      const sourceSplashPath = path.join(brainDir, splashCandidates[splashCandidates.length - 1]);
      console.log(`Found cinematic splash artwork: ${sourceSplashPath}`);
      
      // Save pristine copy in assets
      const splashArtworkDest = path.join(assetsDir, "splash-artwork.png");
      execSync(`magick "${sourceSplashPath}" -resize 1024x1024 -quality 95 "${splashArtworkDest}"`);
      
      // Render splash-icon.png (high resolution 1024x1024 square with smooth rounded corners on dark canvas)
      const splashIconDest = path.join(assetsDir, "splash-icon.png");
      execSync(`magick "${sourceSplashPath}" -resize 1024x1024 -quality 95 "${splashIconDest}"`);
      console.log("✔ Cinematic splash screen rendered at 1024x1024.");
    } else {
      console.warn("⚠ Splash artwork source not found, fallback to master icon for splash-icon.png");
      execSync(`magick "${masterSvgPath}" -resize 1024x1024 "${path.join(assetsDir, "splash-icon.png")}"`);
    }

    console.log("✔ All Penny OS mobile assets generated successfully in frontend/assets/!");
  } finally {
    // Clean up temp directory
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  }
}

main().catch(err => {
  console.error("Asset generation error:", err);
  process.exit(1);
});
