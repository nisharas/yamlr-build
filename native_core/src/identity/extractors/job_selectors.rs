//! Job & CronJob Selector Extractor
//!
//! Why: Extracts selector matchLabels for batch Jobs and CronJobs to track pod ownership
//! and verify controller-uid label bindings.

use super::{iter_shard_paths, NativeMetadataExtractor};
use crate::models::{NativeIdentity, NativeShard};

pub struct JobSelectorExtractor;

impl NativeMetadataExtractor for JobSelectorExtractor {
    fn name(&self) -> &'static str {
        "JobSelectorExtractor"
    }

    fn extract(&self, shards: &[NativeShard], identity: &mut NativeIdentity) {
        if identity.kind != "Job" && identity.kind != "CronJob" {
            return;
        }

        let paths = iter_shard_paths(shards);
        for (path, s) in paths {
            if path.contains("selector") && !s.key.is_empty() {
                if let Some(val) = &s.value {
                    let clean = val.trim_matches(|c| c == '"' || c == '\'').to_string();
                    identity.selector.insert(s.key.clone(), clean);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_job_selectors() {
        let raw = "apiVersion: batch/v1\nkind: Job\nmetadata:\n  name: migrate\nspec:\n  selector:\n    matchLabels:\n      job-name: migrate";
        let shards = crate::sharder::native_shard(raw);
        let mut id = NativeIdentity {
            kind: "Job".to_string(),
            name: "migrate".to_string(),
            ..Default::default()
        };
        JobSelectorExtractor.extract(&shards, &mut id);
        assert_eq!(id.selector.get("job-name"), Some(&"migrate".to_string()));
    }
}
