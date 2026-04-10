import * as vscode from 'vscode';
import * as path from 'path';

let client: any = null;

export function activate(context: vscode.ExtensionContext) {
    // 🛡️ LEVEL 0: Instant Heartbeat (Status Bar Priority)
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(shield) Yamlr: Active';
    statusBarItem.tooltip = 'Yamlr Safety Engine is connected.';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    try {
        console.log('Yamlr: Activation sequence initiated.');
        vscode.window.showInformationMessage('Yamlr Safety Engine: Initializing...');

        // 🛡️ LEVEL 1: Late-Binding Imports (Prevent early crashes if libraries are missing)
        const { LanguageClient, TransportKind } = require('vscode-languageclient/node');
        const fs = require('fs');
        const os = require('os');

        const outputChannel = vscode.window.createOutputChannel('Yamlr Server');
        outputChannel.appendLine('🚀 Yamlr Forensic Safety Engine: Log Stream Active');

        const config = vscode.workspace.getConfiguration('yamlr');
        let yamlrPath = config.get<string>('path');
        
        // 🕵️ Sovereign Binary Discovery (Zero-Config)
        const bundledEXE = os.platform() === 'win32' ? 'yamlr.exe' : 'yamlr';
        const bundledPath = context.asAbsolutePath(path.join('bin', bundledEXE));
        
        let binaryExists = false;
        if (yamlrPath && yamlrPath !== 'yamlr') {
            if (fs.existsSync(yamlrPath)) {
                binaryExists = true;
                outputChannel.appendLine(`📡 Using user-configured engine at: ${yamlrPath}`);
            } else {
                outputChannel.appendLine(`⚠️ User-configured path not found: ${yamlrPath}. Falling back...`);
            }
        }

        if (!binaryExists && fs.existsSync(bundledPath)) {
            yamlrPath = bundledPath;
            binaryExists = true;
            outputChannel.appendLine(`✅ Sovereign engine discovered in bundle: ${yamlrPath}`);
        }

        if (!binaryExists) {
            yamlrPath = 'yamlr'; // Fallback to PATH
            outputChannel.appendLine(`🌐 No bundled binary found. Falling back to system 'yamlr'`);
        }

        // Language Client options
        let serverOptions = {
            command: yamlrPath,
            args: ['lsp'],
            transport: TransportKind.stdio,
            options: { env: { ...process.env } }
        };

        let clientOptions = {
            documentSelector: [
                { scheme: 'file', language: 'yaml' },
                { scheme: 'file', language: 'yml' },
                { scheme: 'file', pattern: '**/*.yaml' },
                { scheme: 'file', pattern: '**/*.yml' }
            ],
            synchronize: {
                fileEvents: vscode.workspace.createFileSystemWatcher('**/*.{yaml,yml}')
            },
            outputChannel: outputChannel
        };

        client = new LanguageClient('yamlrLsp', 'Yamlr Safety Engine', serverOptions, clientOptions);
        client.start();
        outputChannel.appendLine('✅ Yamlr Language Client started successfully.');

    } catch (e) {
        // 🛡️ Error Trap: Show exact reason for failure instead of staying silent
        vscode.window.showErrorMessage('Yamlr Critical Failure: ' + e);
        statusBarItem.text = '$(error) Yamlr: Error';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }

}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
