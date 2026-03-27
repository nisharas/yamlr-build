use clap::Parser;
use ignore::WalkBuilder;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::env;
use std::fs::{self, File};
use std::path::{Path, PathBuf};
use std::time::Instant;
use regex::Regex;
use chrono::Utc;
use std::io::Write;

// Payload embedded as Zstd-compressed Tarball

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(required = false)]
    path: Vec<PathBuf>,

    #[arg(short, long)]
    output: Option<String>,

    #[arg(long)]
    worker_path: Option<PathBuf>,
}

#[derive(Serialize, Deserialize, Debug)]
struct Metadata {
    tool: String,
    version: String,
    timestamp: f64,
    duration_seconds: f64,
}

#[derive(Serialize, Deserialize, Debug)]
struct Summary {
    total_files: usize,
    healed_files: usize,
    total_issues: usize,
}

#[derive(Serialize, Deserialize, Debug)]
struct Identity {
    kind: String,
    name: Option<String>,
    namespace: Option<String>,
    api_version: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct Finding {
    analyzer_name: String,
    severity: String,
    message: String,
    rule_id: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct FileResult {
    file_path: String,
    full_path: String,
    success: bool,
    status: String,
    kind: String,
    identities: Vec<Identity>,
    findings: Vec<Finding>,
    health_score: i32,
    timestamp: f64,
    processing_time_seconds: f64,
    written: bool,
    healed_content: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
struct RootOutput {
    metadata: Metadata,
    summary: Summary,
    results: Vec<FileResult>,
}

lazy_static::lazy_static! {
    static ref RE_KIND: Regex = Regex::new(r#"(?i)^kind:\s*['"]?([a-zA-Z0-9.-]+)['"]?"#).unwrap();
    static ref RE_NAME: Regex = Regex::new(r#"(?i)^name:\s*['"]?([a-zA-Z0-9.-]+)['"]?"#).unwrap();
    static ref RE_API: Regex = Regex::new(r#"(?i)^apiVersion:\s*['"]?([a-zA-Z0-9./-]+)['"]?"#).unwrap();
    static ref RE_NS: Regex = Regex::new(r#"(?i)^namespace:\s*['"]?([a-zA-Z0-9.-]+)['"]?"#).unwrap();
}

struct Candidate {
    indent: usize,
    value: String,
}

fn finalize_sovereign(candidates: Vec<Candidate>) -> Option<String> {
    if candidates.is_empty() {
        return None;
    }
    let min_indent = candidates.iter().map(|c| c.indent).min().unwrap();
    let shallowest: Vec<&Candidate> = candidates.iter().filter(|c| c.indent == min_indent).collect();
    
    if shallowest.len() == 1 {
        Some(shallowest[0].value.clone())
    } else {
        None // Collision! Matches Python's _log_identity_collision
    }
}

fn extract_identities(content: &str) -> Vec<Identity> {
    let mut identities = Vec::new();
    
    for doc in content.split("---") {
        if doc.trim().is_empty() {
            continue;
        }

        let mut kinds = Vec::new();
        let mut names = Vec::new();
        let mut apis = Vec::new();
        let mut nss = Vec::new();

        for line in doc.lines() {
            let indent = line.chars().take_while(|c| c.is_whitespace()).count();
            let trimmed = line.trim();
            
            if let Some(caps) = RE_KIND.captures(trimmed) {
                kinds.push(Candidate { indent, value: caps[1].to_string() });
            }
            if let Some(caps) = RE_NAME.captures(trimmed) {
                names.push(Candidate { indent, value: caps[1].to_string() });
            }
            if let Some(caps) = RE_API.captures(trimmed) {
                apis.push(Candidate { indent, value: caps[1].to_string() });
            }
            if let Some(caps) = RE_NS.captures(trimmed) {
                nss.push(Candidate { indent, value: caps[1].to_string() });
            }
        }

        let kind = finalize_sovereign(kinds);
        let api = finalize_sovereign(apis);
        let name = finalize_sovereign(names);
        let ns = finalize_sovereign(nss);

        // OSS Filter Path: scanner_identity.py line 175 requires BOTH kind AND api_version
        if kind.is_some() && api.is_some() {
            identities.push(Identity {
                kind: kind.unwrap(),
                name,
                namespace: ns,
                api_version: api,
            });
        }
    }
    identities
}

fn process_file(path: &Path, start_time: f64) -> Option<FileResult> {
    let content = fs::read_to_string(path).ok()?;
    let start = Instant::now();
    let identities = extract_identities(&content);
    
    let main_kind = identities.first().map(|i| i.kind.clone()).unwrap_or_else(|| "Unknown".to_string());
    
    // Normalize path to match Python's relative formatting if possible
    let file_path = path.to_string_lossy().to_string();
    
    Some(FileResult {
        file_path,
        full_path: fs::canonicalize(path).unwrap_or(path.to_path_buf()).to_string_lossy().to_string(),
        success: true,
        status: "UNCHANGED".to_string(),
        kind: main_kind,
        identities,
        findings: Vec::new(), 
        health_score: 100,
        timestamp: start_time,
        processing_time_seconds: start.elapsed().as_secs_f64(),
        written: false,
        healed_content: Some(content),
    })
}

#[cfg(windows)]
const WORKER_PAYLOAD: &[u8] = include_bytes!("../../../yamlr-worker.tar.zst");
#[cfg(not(windows))]
const WORKER_PAYLOAD: &[u8] = include_bytes!("../../../yamlr-worker-linux.tar.zst"); // Placeholder

fn get_worker_dir() -> PathBuf {
    let home = if cfg!(windows) {
        env::var("USERPROFILE").unwrap_or_else(|_| ".".to_string())
    } else {
        env::var("HOME").unwrap_or_else(|_| ".".to_string())
    };
    
    let mut path = PathBuf::from(home);
    path.push(".yamlr");
    path.push("bin");
    path.push("worker-v0.2.1"); // Bump version for new format
    path
}

fn ensure_worker_extracted() -> PathBuf {
    let worker_dir = get_worker_dir();
    let ext = if cfg!(windows) { ".exe" } else { "" };
    let exe_path = worker_dir.join(format!("yamlr-worker{}", ext));

    if !exe_path.exists() {
        if worker_dir.exists() {
            fs::remove_dir_all(&worker_dir).ok();
        }
        fs::create_dir_all(&worker_dir).expect("Failed to create worker directory");
        
        let decoder = zstd::stream::read::Decoder::new(std::io::Cursor::new(WORKER_PAYLOAD))
            .expect("Failed to create zstd decoder");
        let mut archive = tar::Archive::new(decoder);
        archive.unpack(&worker_dir).expect("Failed to unpack worker archive");

        #[cfg(unix)]
        {
            // Tar crate usually handles permissions, but let's ensure the main exe is runnable
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&exe_path).unwrap().permissions();
            perms.set_mode(0o755);
            fs::set_permissions(&exe_path, perms).ok();
        }
    }
    exe_path
}

fn main() {
    let args = Args::parse();
    
    // For now, if no path is provided, we just print help or extract worker
    if args.path.is_empty() {
        println!("Yamlr Orchestrator v0.2.0 (Rust)");
        let worker = ensure_worker_extracted();
        println!("Worker extracted to: {:?}", worker);
        return;
    }

    let global_start = Instant::now();
    let timestamp = Utc::now().timestamp() as f64;

    let mut builder = WalkBuilder::new(&args.path[0]);
    for p in args.path.iter().skip(1) {
        builder.add(p);
    }
    
    let walker = builder.threads(num_cpus::get()).build();

    let paths: Vec<PathBuf> = walker
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().map(|ft| ft.is_file()).unwrap_or(false))
        .filter(|e| {
            let p = e.path();
            p.extension().map_or(false, |ext| ext == "yaml" || ext == "yml")
        })
        .map(|e| e.path().to_path_buf())
        .collect();

    let results: Vec<FileResult> = paths
        .par_iter()
        .filter_map(|p| process_file(p, timestamp))
        .collect();

    let duration = global_start.elapsed().as_secs_f64();
    
    let output = RootOutput {
        metadata: Metadata {
            tool: "Yamlr".to_string(),
            version: "0.2.0-rust".to_string(),
            timestamp,
            duration_seconds: duration,
        },
        summary: Summary {
            total_files: results.len(),
            healed_files: 0,
            total_issues: 0,
        },
        results,
    };

    if let Some(format) = args.output {
        if format == "json" {
            println!("{}", serde_json::to_string_pretty(&output).unwrap());
        }
    } else {
        println!("Rust Scanner (yamlr-light) v0.2.0");
        println!("Scanned {} K8s resources in {:.4}s", output.summary.total_files, duration);
    }
}
