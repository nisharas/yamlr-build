"""Repository rules for hermetically downloading pre-compiled static Yamlr binaries."""

def _yamlr_binary_impl(ctx):
    ctx.download_and_extract(
        url = ctx.attr.url,
        sha256 = ctx.attr.sha256,
        type = ctx.attr.type,
    )
    build_content = """package(default_visibility = ["//visibility:public"])
exports_files(["{}"])
""".format(ctx.attr.binary_name)
    ctx.file("BUILD.bazel", build_content)

yamlr_download = repository_rule(
    implementation = _yamlr_binary_impl,
    attrs = {
        "url": attr.string(mandatory = True),
        "sha256": attr.string(mandatory = False),
        "type": attr.string(default = "tar.gz"),
        "binary_name": attr.string(default = "yamlr"),
    },
)

def yamlr_register_toolchains(version = "0.1.0"):
    """Registers pre-compiled static Yamlr binaries for hermetic execution."""
    yamlr_download(
        name = "yamlr_linux_amd64",
        url = "https://github.com/yamlr/yamlr/releases/download/v{}/yamlr-linux-x86_64.tar.gz".format(version),
        binary_name = "yamlr",
    )
    yamlr_download(
        name = "yamlr_darwin_arm64",
        url = "https://github.com/yamlr/yamlr/releases/download/v{}/yamlr-macos-aarch64.tar.gz".format(version),
        binary_name = "yamlr",
    )
    yamlr_download(
        name = "yamlr_windows_amd64",
        url = "https://github.com/yamlr/yamlr/releases/download/v{}/yamlr-windows-x86_64.zip".format(version),
        binary_name = "yamlr.exe",
        type = "zip",
    )
