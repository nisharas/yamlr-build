/**
 * Yamlr — Autonomous Resolution Plane for Kubernetes Manifests
 * C-ABI Header File for Foreign Language Embedding ("Intel Inside")
 * 
 * Copyright (c) 2026 Timonel Labs. Proprietary and confidential; use is governed by the Yamlr license.
 */

#ifndef YAMLR_H
#define YAMLR_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Heals a Kubernetes manifest string in-memory with lossless comment preservation.
 * Returns an allocated C-string that MUST be freed using yamlr_free_string().
 */
char* yamlr_heal_manifest(const char* manifest);

/**
 * Validates a Kubernetes manifest string against loaded OpenAPI schemas.
 * Returns the number of violations, or -1 on error.
 */
int yamlr_validate_manifest(const char* manifest, const char* k8s_version);

/**
 * Computes a unified diff preview of proposed auto-remediations.
 * Returns an allocated C-string that MUST be freed using yamlr_free_string().
 */
char* yamlr_diff_manifest(const char* manifest);

/**
 * Formats a Kubernetes manifest string according to official schema hierarchy (k8sfmt).
 * Returns an allocated C-string that MUST be freed using yamlr_free_string().
 */
char* yamlr_format_manifest(const char* manifest);

/**
 * Returns the current Yamlr native engine version string.
 * Returns an allocated C-string that MUST be freed using yamlr_free_string().
 */
char* yamlr_version(void);

/**
 * Frees a C-string allocated by the Yamlr C-FFI.
 */
void yamlr_free_string(char* ptr);

#ifdef __cplusplus
}
#endif

#endif /* YAMLR_H */
