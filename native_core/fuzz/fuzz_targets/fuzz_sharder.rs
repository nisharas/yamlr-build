#![no_main]
use libfuzzer_sys::fuzz_target;
use yamlr_native::{native_shard, native_reconstruct_yaml};

fuzz_target!(|data: &[u8]| {
    if let Ok(s) = std::str::from_utf8(data) {
        // Fuzz the sharding and reconstruction pipeline
        let shards = native_shard(s);
        let _reconstructed = native_reconstruct_yaml(&shards);
    }
});
