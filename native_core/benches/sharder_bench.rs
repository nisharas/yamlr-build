use criterion::{black_box, criterion_group, criterion_main, Criterion, Throughput};
use yamlr_native::schemas::{native_get_schema_for_version, native_validate_ast_against_schema};
use yamlr_native::sharder::native_shard;
use yamlr_native::structurer::native_structurize;

const SAMPLE_K8S_DEPLOYMENT: &str = r#"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: production
  labels:
    app: nginx
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.4
        ports:
        - containerPort: 80
        resources:
          limits:
            cpu: "500m"
            memory: "512Mi"
          requests:
            cpu: "100m"
            memory: "128Mi"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 80
          initialDelaySeconds: 15
          periodSeconds: 20
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
"#;

fn bench_sharder(c: &mut Criterion) {
    let mut group = c.benchmark_group("yamlr_native_sharding");
    group.throughput(Throughput::Bytes(SAMPLE_K8S_DEPLOYMENT.len() as u64));

    group.bench_function("shard_k8s_deployment", |b| {
        b.iter(|| native_shard(black_box(SAMPLE_K8S_DEPLOYMENT)))
    });

    group.finish();
}

fn bench_structurer(c: &mut Criterion) {
    let shards = native_shard(SAMPLE_K8S_DEPLOYMENT);
    let mut group = c.benchmark_group("yamlr_native_structurer");

    group.bench_function("structurize_arena_tree", |b| {
        b.iter(|| native_structurize(black_box(shards.clone())))
    });

    group.finish();
}

fn bench_schema_validation(c: &mut Criterion) {
    let shards = native_shard(SAMPLE_K8S_DEPLOYMENT);
    let manifest = native_structurize(shards);
    let schemas = native_get_schema_for_version("1.30");

    let mut group = c.benchmark_group("yamlr_native_ast_schema");

    group.bench_function("validate_ast_schema_v1_30", |b| {
        b.iter(|| native_validate_ast_against_schema(black_box(&manifest), black_box(&schemas)))
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_sharder,
    bench_structurer,
    bench_schema_validation
);
criterion_main!(benches);
