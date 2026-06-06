const { execSync } = require("child_process");

function build_tailwind() {
    execSync("npx tailwindcss -i ./styles/global.css -o ./styles/output.css");
    return "Tailwind built";
}

module.exports = {
    build_tailwind
};