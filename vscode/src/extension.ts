import * as vscode from 'vscode';
import * as path from 'path';

let client: any = null;

export function activate(context: vscode.ExtensionContext) {
    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = '$(shield) Yamlr: Active';
    statusBarItem.tooltip = 'Yamlr is connected.';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    try {
        console.log('Yamlr: Activation sequence initiated.');
        vscode.window.showInformationMessage('Yamlr: Initializing...');

        // Late-binding imports
        const { LanguageClient, TransportKind } = require('vscode-languageclient/node');
        const fs = require('fs');
        const os = require('os');

        const outputChannel = vscode.window.createOutputChannel('Yamlr Server');
        outputChannel.appendLine('Yamlr Server: Log Stream Active');

        const config = vscode.workspace.getConfiguration('yamlr');
        let yamlrPath = config.get<string>('binaryPath') || config.get<string>('path');
        
        // Multi-tier Native Binary Discovery
        const bundledEXE = os.platform() === 'win32' ? 'yamlr.exe' : 'yamlr';
        let binaryExists = false;

        // 1. User-configured custom binary path
        if (yamlrPath && yamlrPath !== 'yamlr') {
            if (fs.existsSync(yamlrPath)) {
                binaryExists = true;
                outputChannel.appendLine(`Using user-configured engine at: ${yamlrPath}`);
            } else {
                outputChannel.appendLine(`User-configured path not found: ${yamlrPath}. Falling back...`);
            }
        }

        // 2. Workspace local development builds
        if (!binaryExists && vscode.workspace.workspaceFolders) {
            for (const folder of vscode.workspace.workspaceFolders) {
                const candidates = [
                    path.join(folder.uri.fsPath, 'bin', bundledEXE),
                    path.join(folder.uri.fsPath, 'native_core', 'target', 'release', bundledEXE),
                    path.join(folder.uri.fsPath, 'target', 'release', bundledEXE),
                ];
                for (const candidate of candidates) {
                    if (fs.existsSync(candidate)) {
                        yamlrPath = candidate;
                        binaryExists = true;
                        outputChannel.appendLine(`Found workspace binary at: ${yamlrPath}`);
                        break;
                    }
                }
                if (binaryExists) break;
            }
        }

        // 3. Bundled extension binary
        if (!binaryExists) {
            const bundledPath = context.asAbsolutePath(path.join('bin', bundledEXE));
            if (fs.existsSync(bundledPath)) {
                yamlrPath = bundledPath;
                binaryExists = true;
                outputChannel.appendLine(`Engine discovered in extension bundle: ${yamlrPath}`);
            }
        }

        // 4. Default user installation paths (~/.local/bin or %LOCALAPPDATA%\yamlr\bin)
        if (!binaryExists) {
            const userHomeCandidate = os.platform() === 'win32'
                ? path.join(process.env.LOCALAPPDATA || '', 'yamlr', 'bin', bundledEXE)
                : path.join(process.env.HOME || '', '.local', 'bin', bundledEXE);

            if (userHomeCandidate && fs.existsSync(userHomeCandidate)) {
                yamlrPath = userHomeCandidate;
                binaryExists = true;
                outputChannel.appendLine(`Engine discovered in user profile: ${yamlrPath}`);
            }
        }

        // 5. System PATH fallback
        if (!binaryExists) {
            yamlrPath = 'yamlr';
            outputChannel.appendLine(`No direct binary path located. Delegating to system PATH ('yamlr')`);
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

        client = new LanguageClient('yamlrLsp', 'Yamlr Engine', serverOptions, clientOptions);
        client.start();
        outputChannel.appendLine('Yamlr Language Client started successfully.');

        // Register yamlr.fixAll command
        const fixAllDisposable = vscode.commands.registerCommand('yamlr.fixAll', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showInformationMessage('Yamlr: No active editor.');
                return;
            }
            const doc = editor.document;
            if (doc.languageId !== 'yaml' && doc.languageId !== 'yml') {
                vscode.window.showInformationMessage('Yamlr: Active document is not a YAML file.');
                return;
            }
            try {
                const actions: vscode.CodeAction[] = await vscode.commands.executeCommand(
                    'vscode.executeCodeActionProvider',
                    doc.uri,
                    new vscode.Range(0, 0, doc.lineCount, 0),
                    'source.fixAll.yamlr'
                );
                if (actions && actions.length > 0) {
                    for (const action of actions) {
                        if (action.edit) {
                            await vscode.workspace.applyEdit(action.edit);
                        } else if (action.command) {
                            await vscode.commands.executeCommand(action.command.command, ...(action.command.arguments || []));
                        }
                    }
                    vscode.window.showInformationMessage('Yamlr: Manifest repaired successfully.');
                } else {
                    vscode.window.showInformationMessage('Yamlr: No automated repairs required.');
                }
            } catch (err) {
                vscode.window.showErrorMessage(`Yamlr Fix All Error: ${err}`);
            }
        });
        context.subscriptions.push(fixAllDisposable);

    } catch (e) {
        // Display failure reason
        vscode.window.showErrorMessage('Yamlr Error: ' + e);
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
