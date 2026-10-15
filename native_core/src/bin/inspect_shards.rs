use yamlr_native::sharder::native_shard;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let content = if args.len() > 1 {
        std::fs::read_to_string(&args[1]).unwrap()
    } else {
        "apiVersion v1\nkind: ConfigMap\n".to_string()
    };
    let shards = native_shard(&content);
    for s in &shards {
        println!("L{}: raw={:?}, key={:?}, val={:?}", s.line_no, s.raw_line, s.key, s.value);
    }
}
