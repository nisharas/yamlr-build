//! C-Compatible Foreign Function Interface (FFI) for Embedding Yamlr.
//!
//! Why: Enables third-party engines (Go, C/C++, Rust, Python, WASM) to consume Yamlr
//! as an embeddable shared library ("Intel Inside"). Strictly < 500 lines.

use crate::cli::heal_cmd::heal_manifest_string;
use crate::schemas::native_get_schema_for_version;
use crate::sharder::native_shard;
use crate::structurer::native_structurize;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

/// Heals a Kubernetes manifest string in-memory and returns an allocated C-string.
/// Caller must free the returned string using `yamlr_free_string`.
#[no_mangle]
pub extern "C" fn yamlr_heal_manifest(c_manifest: *const c_char) -> *mut c_char {
    if c_manifest.is_null() {
        return std::ptr::null_mut();
    }

    let c_str = unsafe { CStr::from_ptr(c_manifest) };
    let manifest = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let (healed, _) = heal_manifest_string(manifest);
    match CString::new(healed) {
        Ok(c_res) => c_res.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Validates a Kubernetes manifest string against schemas and returns violation count.
#[no_mangle]
pub extern "C" fn yamlr_validate_manifest(
    c_manifest: *const c_char,
    c_k8s_version: *const c_char,
) -> i32 {
    if c_manifest.is_null() {
        return -1;
    }

    let manifest_str = match unsafe { CStr::from_ptr(c_manifest) }.to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };

    let ver_str = if c_k8s_version.is_null() {
        "1.30"
    } else {
        match unsafe { CStr::from_ptr(c_k8s_version) }.to_str() {
            Ok(s) => s,
            Err(_) => "1.30",
        }
    };

    let schemas = native_get_schema_for_version(ver_str);
    let shards = native_shard(manifest_str);
    if shards.is_empty() {
        return 0;
    }

    let parsed = native_structurize(shards);
    let violations = crate::schemas::native_validate_ast_against_schema(&parsed, &schemas);
    (violations.len() + parsed.integrity_violations.len()) as i32
}

/// Computes unified diff preview of proposed auto-remediations for a manifest.
/// Caller must free returned string using `yamlr_free_string`.
#[no_mangle]
pub extern "C" fn yamlr_diff_manifest(c_manifest: *const c_char) -> *mut c_char {
    if c_manifest.is_null() {
        return std::ptr::null_mut();
    }

    let c_str = unsafe { CStr::from_ptr(c_manifest) };
    let manifest = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let (healed, _) = heal_manifest_string(manifest);
    let diff = crate::wasm::wasm_diff(manifest, &healed);
    match CString::new(diff) {
        Ok(c_res) => c_res.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Formats a Kubernetes manifest string according to official schema hierarchy (k8sfmt).
/// Caller must free returned string using `yamlr_free_string`.
#[no_mangle]
pub extern "C" fn yamlr_format_manifest(c_manifest: *const c_char) -> *mut c_char {
    if c_manifest.is_null() {
        return std::ptr::null_mut();
    }

    let c_str = unsafe { CStr::from_ptr(c_manifest) };
    let manifest = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let formatted = crate::cli::fmt_cmd::format_manifest_content(manifest);
    match CString::new(formatted) {
        Ok(c_res) => c_res.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Returns the current Yamlr native engine version string.
/// Caller must free returned string using `yamlr_free_string`.
#[no_mangle]
pub extern "C" fn yamlr_version() -> *mut c_char {
    match CString::new(env!("CARGO_PKG_VERSION")) {
        Ok(c_res) => c_res.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Frees a C-string allocated by the Yamlr C-FFI.
#[no_mangle]
pub extern "C" fn yamlr_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_c_ffi_healing_and_free() {
        let manifest = CString::new("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: my-app\nspec:\n  template:\n    spec:\n      containers:\n        - name: web\n          image: nginx:latest\n").unwrap();
        let healed_ptr = yamlr_heal_manifest(manifest.as_ptr());
        assert!(!healed_ptr.is_null());

        let healed_cstr = unsafe { CStr::from_ptr(healed_ptr) };
        let healed_str = healed_cstr.to_str().unwrap();
        assert!(healed_str.contains("my-app"));

        yamlr_free_string(healed_ptr);
    }

    #[test]
    fn test_c_ffi_version_and_diff() {
        let ver_ptr = yamlr_version();
        assert!(!ver_ptr.is_null());
        let ver_str = unsafe { CStr::from_ptr(ver_ptr) }.to_str().unwrap();
        assert_eq!(ver_str, "0.1.0");
        yamlr_free_string(ver_ptr);

        let manifest =
            CString::new("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: test-app\n")
                .unwrap();
        let diff_ptr = yamlr_diff_manifest(manifest.as_ptr());
        assert!(!diff_ptr.is_null());
        yamlr_free_string(diff_ptr);
    }
}
