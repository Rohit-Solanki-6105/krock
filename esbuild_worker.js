const esbuild = require("esbuild");
const path = require("path");
const alias = require("esbuild-plugin-alias");


const platform = process.argv[2]; // 'browser' | 'node'
const entry = process.argv[3];
const outfile = process.argv[4];

esbuild.build({
    entryPoints: [entry],
    bundle: true,
    outfile: outfile,
    platform: platform,
    format: platform === "browser" ? "iife" : "cjs",
    loader: {
        ".tsx": "tsx",
        ".ts": "ts",
        ".jsx": "jsx",
        ".js": "js"
    },
    jsx: "automatic",
    plugins: [
        alias({
            "@": path.resolve(__dirname)
        })
    ]
}).then(() => {
    // console.log(`Built ${platform} bundle: ${outfile}`);
}).catch((err) => {
    console.error(err);
    process.exit(1);
});
