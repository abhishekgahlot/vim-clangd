# LSP Client
# https://github.com/Microsoft/language-server-protocol/blob/master/protocol.md
from jsonrpc import JsonRPCClient
import glog as log
import os

Initialize_REQUEST = 'initialize'
Shutdown_REQUEST = 'shutdown'
Exit_NOTIFICATION = 'exit'

Completion_REQUEST = 'textDocument/completion'

Initialized_NOTIFICATION = 'initialized'
DidOpenTextDocument_NOTIFICATION = 'textDocument/didOpen'
DidChangeTextDocument_NOTIFICATION = 'textDocument/didChange'
DidSaveTextDocument_NOTIFICATION = 'textDocument/didSave'
DidCloseTextDocument_NOTIFICATION = 'textDocument/didClose'

PublishDiagnostics_NOTIFICATION = 'textDocument/publishDiagnostics'


class LSPClient():
    def __init__(self, input_fd, output_fd):
        self._rpcclient = JsonRPCClient(self, input_fd, output_fd)
        self._documents = {}

    def initialize(self):
        rr = self._rpcclient.sendRequest(Initialize_REQUEST, {
            'processId': os.getpid(),
            'rootUri': 'file://' + os.getcwd(),
            'capabilities': {},
            'trace': 'off'
        })
        log.info('clangd connected with piped fd')
        log.info('clangd capabilities: %s' % rr['capabilities'])
        return rr

    def onNotification(self, method, params):
        if method == PublishDiagnostics_NOTIFICATION:
            self.onDiagnostics(params['uri'], params['diagnostics'])
        pass

    def onRequest(self, method, params):
        pass

    def onResponse(self, request, response):
        pass

    def onInitialized(self):
        return self._rpcclient.sendNotification(Initialized_NOTIFICATION)

    def shutdown(self):
        return self._rpcclient.sendRequest(Shutdown_REQUEST, nullResponse=True)

    def exit(self):
        return self._rpcclient.sendNotification(Exit_NOTIFICATION)

    def handleClientRequests(self):
        self._rpcclient.handleRecv()

    # notifications
    def didOpenTestDocument(self, uri, text):
        self._documents[uri] = {}
        self._documents[uri]['version'] = 1
        return self._rpcclient.sendNotification(
            DidOpenTextDocument_NOTIFICATION, {
                'textDocument': {
                    'uri': uri,
                    'languageId': 'c',
                    'version': 1,
                    'text': text
                }
            })

    def didChangeTestDocument(self, uri, content):
        version = self._documents[uri][
            'version'] = self._documents[uri]['version'] + 1
        return self._rpcclient.sendNotification(
            DidChangeTextDocument_NOTIFICATION, {
                'textDocument': {
                    'uri': uri,
                    'version': version
                },
                'contentChanges': [{
                    'text': content
                }]
            })

    def closeAllFiles(self):
        for uri in self._documents.iterkeys():
            self.didCloseTestDocument(uri)

    def didCloseTestDocument(self, uri):
        if not self._documents.has_key(uri):
            return
        version = self._documents.pop(uri)['version']
        return self._rpcclient.sendNotification(
            DidSaveTextDocument_NOTIFICATION, {'textDocument': {
                'uri': uri
            }})

    def didSaveTestDocument(self, uri):
        return self._rpcclient.sendNotification(
            DidCloseTextDocument_NOTIFICATION, {'textDocument': {
                'uri': uri
            }})

    def onDiagnostics(self, uri, diagnostics):
        if not self._documents.has_key(uri):
            return
        log.info('diagnostics for %s is updated' % uri)
        self._documents[uri]['diagnostics'] = diagnostics
        pass

    def getDiagnostics(self, uri):
        self.handleClientRequests()
        if not self._documents[uri].has_key('diagnostics'):
            return None
        return self._documents[uri]['diagnostics']

    def completeAt(self, uri, line, character):
        return self._rpcclient.sendRequest(
            Completion_REQUEST, {
                'textDocument': {
                    'uri': uri,
                    'position': {
                      'line': line,
                      'character': character
                    }
                }
            })
