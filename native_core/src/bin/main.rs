//! Yamlr Standalone Native Binary Entry Point.
//!
//! Ultra-high performance, zero-dependency CLI (<15ms execution).

use std::env;
use std::process::exit;

fn main() {
    let args: Vec<String> = env::args().collect();

    // Structured JSON logging support via tracing crate
    if args.iter().any(|a| a == "--json-log") {
        #[cfg(not(target_arch = "wasm32"))]
        {
            let _ = tracing_subscriber::fmt()
                .json()
                .with_target(false)
                .with_current_span(false)
                .try_init();
            tracing::info!(
                version = env!("CARGO_PKG_VERSION"),
                "yamlr native session initialized"
            );
        }
    }

    let code = yamlr_native::cli::dispatch::run(&args);
    exit(code);
}
