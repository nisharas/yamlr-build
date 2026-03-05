import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration('yamlr');
    let pythonPath = vscode.workspace.getConfiguration('python').get<string>('defaultInterpreterPath') || 'python';

    // Allow user to override python path specifically for yamlr
    const customPython = config.get<string>('pythonPath');
    if (customPython) {
        pythonPath = customPython;
    }

    const serverModule = context.asAbsolutePath(path.join('lsp', 'server.py'));

    const serverOptions: ServerOptions = {
        run: { command: pythonPath, args: [serverModule] },
        debug: { command: pythonPath, args: [serverModule] }
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'yaml' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/.yamlr.yaml')
        },
        initializationOptions: {
            kubeVersion: config.get('kubeVersion', '1.31'),
            strictValidation: config.get('strictValidation', false),
            harden: config.get('harden', false),
            enforceLimits: config.get('enforceLimits', false),
            enforceProbes: config.get('enforceProbes', false)
        }
    };

    client = new LanguageClient(
        'yamlr',
        'Yamlr Optimizer',
        serverOptions,
        clientOptions
    );

    client.start().catch(err => {
        vscode.window.showErrorMessage(`Failed to start Yamlr Language Server: ${err}`);
    });
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
