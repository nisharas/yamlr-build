"""Yamlr Bazel Starlark Rules for hermetic Kubernetes manifest validation and formatting."""

def _yamlr_test_impl(ctx):
    exe = ctx.executable._yamlr
    manifests = ctx.files.srcs
    k8s_version = ctx.attr.k8s_version

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    args = ["--k8s-version", k8s_version]
    manifest_paths = " ".join([f.short_path for f in manifests])

    script_content = """#!/usr/bin/env bash
set -e
{yamlr} scan {args} {manifests}
""".format(
        yamlr = exe.short_path,
        args = " ".join(args),
        manifests = manifest_paths,
    )
    ctx.actions.write(output = script, content = script_content, is_executable = True)

    runfiles = ctx.runfiles(files = manifests + [exe])
    return [DefaultInfo(executable = script, runfiles = runfiles)]

yamlr_test = rule(
    implementation = _yamlr_test_impl,
    test = True,
    attrs = {
        "srcs": attr.label_list(allow_files = [".yaml", ".yml"], mandatory = True, doc = "Kubernetes YAML manifests to validate."),
        "k8s_version": attr.string(default = "1.30", doc = "Target Kubernetes schema release."),
        "_yamlr": attr.label(default = "//yamlr:yamlr_tool", executable = True, cfg = "exec"),
    },
    doc = "Hermetically validates Kubernetes manifests against official schemas.",
)

def _yamlr_fix_impl(ctx):
    exe = ctx.executable._yamlr
    manifests = ctx.files.srcs

    script = ctx.actions.declare_file(ctx.label.name + ".sh")
    manifest_paths = " ".join([f.short_path for f in manifests])

    script_content = """#!/usr/bin/env bash
set -e
{yamlr} fmt -w {manifests}
""".format(
        yamlr = exe.short_path,
        manifests = manifest_paths,
    )
    ctx.actions.write(output = script, content = script_content, is_executable = True)

    runfiles = ctx.runfiles(files = manifests + [exe])
    return [DefaultInfo(executable = script, runfiles = runfiles)]

yamlr_fix = rule(
    implementation = _yamlr_fix_impl,
    executable = True,
    attrs = {
        "srcs": attr.label_list(allow_files = [".yaml", ".yml"], mandatory = True, doc = "Kubernetes YAML manifests to format in-place."),
        "_yamlr": attr.label(default = "//yamlr:yamlr_tool", executable = True, cfg = "exec"),
    },
    doc = "Formats Kubernetes manifests in-place to official schema standards.",
)
