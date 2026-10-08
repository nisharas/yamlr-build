/**
 * Cross-platform build script to compile native core into website/public/wasm.
 *
 * Why: Ensures that `npm run build` uses WebAssembly assets compiled from the
 * current native source instead of silently publishing stale pre-built files.
 */
const { execSync } = require("child_process");
const path = require("path");

console.log("[WASM Build] Compiling Yamlr Native Engine to WebAssembly...");

try {
  execSync(
    "npx wasm-pack build ../native_core --target web --out-dir ../website/public/wasm --no-typescript --release -- --no-default-features --features wasm",
    { stdio: "inherit", cwd: path.join(__dirname, "..") }
  );
  console.log("[WASM Build] Successfully compiled native WebAssembly assets.");
} catch (err) {
  console.error("[WASM Build] Failed to compile current WASM assets:", err.message);
  process.exit(1);
}
