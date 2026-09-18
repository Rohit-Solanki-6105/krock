const readline = require("readline");
const fs = require("fs");

// Stdio IPC worker - No HTTP server, no open ports
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

rl.on("line", (line) => {
    if (!line.trim()) return;

    try {
        const payload = JSON.parse(line);
        const { bundle_path, params } = payload;

        if (!bundle_path || !fs.existsSync(bundle_path)) {
            console.log(JSON.stringify({ error: "Bundle path not found" }));
            return;
        }

        // Clear require cache for updated bundles
        delete require.cache[require.resolve(bundle_path)];

        const origArgv = process.argv;
        process.argv = ["node", bundle_path, JSON.stringify(params || {})];

        let capturedHtml = "";
        const origLog = console.log;
        console.log = (msg) => {
            capturedHtml += msg;
        };

        try {
            require(bundle_path);
        } finally {
            console.log = origLog;
            process.argv = origArgv;
        }

        console.log(JSON.stringify({ html: capturedHtml.trim() }));
    } catch (err) {
        console.log(JSON.stringify({ error: err.stack || String(err) }));
    }
});
