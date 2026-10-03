use super::ConfigurationParser;

/// Terraform HCL configuration parser interface.
pub struct TerraformParser;

impl ConfigurationParser for TerraformParser {
    fn detect_violations(&self, _content: &str) -> Result<Vec<String>, String> {
        // HCL/Terraform parser scheduled for Tier 2+ preview
        Ok(vec![])
    }

    fn heal_non_destructive(&self, content: &str, _patch: &str) -> Result<String, String> {
        // Safe passthrough: preserve original HCL content unchanged
        Ok(content.to_string())
    }

    fn dialect(&self) -> &str {
        "terraform"
    }
}
