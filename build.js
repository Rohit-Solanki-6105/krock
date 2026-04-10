const esbuild = require("esbuild");
const path = require("path");
const alias = require("esbuild-plugin-alias");

const isDev = process.env.NODE_ENV !== "production";

esbuild.build({
  entryPoints: ["pages/index.tsx"],
  bundle: true,
  outfile: "public/_bundle.js",

  platform: "browser",
  format: "iife",
  sourcemap: isDev,
  minify: !isDev,

  resolveExtensions: [
    ".tsx",
    ".ts",
    ".jsx",
    ".js",
    ".css",
    ".json"
  ],

  loader: {
    ".tsx": "tsx",
    ".ts": "ts",
    ".jsx": "jsx",
    ".js": "js",
    ".css": "css",
    ".json": "json",
    ".png": "file",
    ".jpg": "file",
    ".svg": "file"
  },

  plugins: [
    alias({
      "@": path.resolve(__dirname)
    })
  ],

  watch: isDev
    ? {
        onRebuild(error) {
          if (error) console.log("❌ Rebuild failed:", error);
          else console.log("✅ Rebuilt successfully");
        }
      }
    : false,

}).then(() => {
  console.log("🚀 React build started...");
}).catch(() => process.exit(1));