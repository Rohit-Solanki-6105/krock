const esbuild = require("esbuild");
const path = require("path");
const alias = require("esbuild-plugin-alias");

async function test() {
    console.log("Testing browser bundle...");
    await esbuild.build({
        entryPoints: ["pages/index.tsx"],
        bundle: true,
        outfile: ".krypter_tmp/test_browser.js",
        platform: "browser",
        format: "iife",
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
    });
    console.log("Testing node bundle...");
    await esbuild.build({
        entryPoints: ["pages/index.tsx"],
        bundle: true,
        outfile: ".krypter_tmp/test_node.js",
        platform: "node",
        format: "cjs",
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
    });
    console.log("Done");
}
test();
