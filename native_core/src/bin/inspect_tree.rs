use yamlr_native::sharder::native_shard;
use yamlr_native::structurer::native_structurize;

fn print_node(node: &yamlr_native::models::SemanticNode, indent: usize) {
    println!("{:indent$}key={:?}, val={:?}, children={}", "", node.key, node.value, node.children.len(), indent=indent);
    for c in &node.children {
        print_node(c, indent + 2);
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = if args.len() > 1 { &args[1] } else { "d:/yamlr/corpus/fleet/category_a_helm_block6/victoriametrics__victoria-metrics-auth/Chart.yaml" };
    let raw = std::fs::read_to_string(path).unwrap();
    let shards = native_shard(&raw);
    for s in &shards {
        if s.line_no >= 20 && s.line_no <= 25 {
            println!("SHARD line={} indent={} key={:?} val={:?} raw={:?} comment={:?} is_tc={}", s.line_no, s.indent, s.key, s.value, s.raw_line, s.comment, s.is_table_continuation);
        }
    }
    let manifest = native_structurize(shards);
    print_node(&manifest.root, 0);
}
