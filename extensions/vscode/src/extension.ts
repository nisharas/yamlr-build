import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    Executable
} from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

export function activate(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration('yamlr');
    const executablePath = config.get<string>('executablePath') || 'yamlr';

    // 1. Configure Language Server Process (yamlr lsp)
    const serverExecutable: Executable = {
        command: executablePath,
        args: ['lsp'],
        options: {
            shell: true
        }
    };

    const serverOptions: ServerOptions = {
        run: serverExecutable,
        debug: serverExecutable
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'yaml' },
            { scheme: 'file', pattern: '**/*.{yaml,yml}' }
        ],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.{yaml,yml}')
        }
    };

    // 2. Start LSP Client
    client = new LanguageClient(
        'yamlrLsp',
        'Yamlr Kubernetes Language Server',
        serverOptions,
        clientOptions
    );

    client.start().catch((err) => {
        vscode.window.showWarningMessage(
            `Yamlr: Could not start LSP server from '${executablePath}'. Ensure yamlr is installed and in PATH.`
        );
    });

    // 3. Register "Heal Active Manifest" Command
    const healCommand = vscode.commands.registerCommand('yamlr.healActiveFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || !editor.document.fileName.match(/\.(yaml|yml)$/)) {
            vscode.window.showInformationMessage('Yamlr: Please open a Kubernetes YAML file to heal.');
            return;
        }

        const filePath = editor.document.fileName;
        const terminal = vscode.window.createTerminal('Yamlr');
        terminal.show();
        terminal.sendText(`${executablePath} heal "${filePath}" --apply`);
    });

    // 4. Register "Scan Workspace" Command
    const scanCommand = vscode.commands.registerCommand('yamlr.scanWorkspace', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showInformationMessage('Yamlr: No workspace folder open.');
            return;
        }

        const terminal = vscode.window.createTerminal('Yamlr');
        terminal.show();
        terminal.sendText(`${executablePath} scan .`);
    });

    context.subscriptions.push(healCommand, scanCommand);
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
