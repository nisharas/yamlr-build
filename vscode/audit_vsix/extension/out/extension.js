"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const node_1 = require("vscode-languageclient/node");
let client;
function activate(context) {
    // 🛡 FAILURE-PROOF START: Create Status Bar immediately
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = `$(shield) Yamlr: Active`;
    statusBarItem.tooltip = 'Yamlr Safety Engine is connected.';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    try {
        console.log('Yamlr: Activation sequence initiated.');
        vscode.window.showInformationMessage('Yamlr Safety Engine: Initializing...');
        const config = vscode.workspace.getConfiguration('yamlr');
        let yamlrPath = config.get('path');
        // 🕵️ Sovereign Binary Discovery (Zero-Config)
        const bundledPath = context.asAbsolutePath(path.join('bin', 'yamlr.exe'));
        const fs = require('fs');
        if (!yamlrPath && fs.existsSync(bundledPath)) {
            yamlrPath = bundledPath;
            console.log(`Yamlr: Sovereign engine discovered at ${yamlrPath}`);
        }
        else {
            yamlrPath = yamlrPath || 'yamlr';
            console.log(`Yamlr: Using engine at ${yamlrPath}`);
        }
        // Language Client options
        let serverOptions = {
            command: yamlrPath,
            args: ['lsp'],
            transport: node_1.TransportKind.stdio,
            options: { env: { ...process.env } }
        };
        let clientOptions = {
            documentSelector: [{ scheme: 'file', language: 'yaml' }],
            synchronize: {
                fileEvents: vscode.workspace.createFileSystemWatcher('**/*.{yaml,yml}')
            }
        };
        client = new node_1.LanguageClient('yamlrLsp', 'Yamlr Safety Engine', serverOptions, clientOptions);
        client.start();
    }
    catch (e) {
        vscode.window.showErrorMessage(`Yamlr: Activation Error - ${e}`);
        statusBarItem.text = `$(error) Yamlr: Error`;
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }
    // Register Heal Command
    let disposable = vscode.commands.registerCommand('yamlr.healFile', async (uri, ruleId) => {
        const targetUri = uri || vscode.window.activeTextEditor?.document.uri;
        if (!targetUri) {
            vscode.window.showErrorMessage('Yamlr: No manifest focused for healing.');
            return;
        }
        const filePath = targetUri.fsPath;
        const terminal = vscode.window.createTerminal(`Yamlr Healing`);
        terminal.show();
        // Execute the CLI healing command
        const healCmd = ruleId ? `yamlr heal "${filePath}" --fix-tags ${ruleId} --yes-all` : `yamlr heal "${filePath}" --yes-all`;
        terminal.sendText(healCmd);
    });
    context.subscriptions.push(disposable);
}
function deactivate() {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
//# sourceMappingURL=extension.js.map