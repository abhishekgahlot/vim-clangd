# LSP Client
# https://github.com/Microsoft/language-server-protocol/blob/master/protocol.md
from jsonrpc import JsonRPCClient
from subprocess import check_output, CalledProcessError, Popen
from signal import signal, SIGCHLD, SIG_IGN
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

def StartProcess(name, clangd_log_path = None):
    from os import pipe, devnull
    if not clangd_log_path:
        clangd_log_path = devnull
    fdClangd = open(clangd_log_path, 'w+')
    fdInRead, fdInWrite = pipe()
    fdOutRead, fdOutWrite = pipe()
    clangd = Popen(name, stdin=fdInRead, stdout=fdOutWrite, stderr=fdClangd)
    return clangd, fdInWrite, fdOutRead, fdClangd


class LSPClient():
    def __init__(self, clangd_executable, clangd_log_path, manager):
        clangd, fdRead, fdWrite, fdClangd = StartProcess(
            clangd_executable, clangd_log_path)
        log.info('clangd started, pid %d' % clangd.pid)
        self._clangd = clangd
        self._clangd_logfd = fdClangd
        self._rpcclient = JsonRPCClient(self, fdRead, fdWrite)
        self._is_alive = True
        self._documents = {}
        self._manager = manager
        self.RegisterSignalHandler()

    def RegisterSignalHandler(self):
        signal(SIGCHLD, lambda signal, frname: self.onServerDown())

    def DeregisterSignalHandler(self):
        signal(SIGCHLD, SIG_IGN)

    def CleanUp(self):
        self.DeregisterSignalHandler()
        if self._clangd.poll() == None:
            self._clangd.terminate()
        if self._clangd.poll() == None:
            self._clangd.kill()
        log.info('clangd stopped, pid %d' % self._clangd.pid)
        self._clangd_logfd.close()

    def isAlive(self):
        return self._is_alive and self._clangd.poll() == None

    def onNotification(self, method, params):
        if method == PublishDiagnostics_NOTIFICATION:
            self.onDiagnostics(params['uri'], params['diagnostics'])
        pass

    def onRequest(self, method, params):
        pass

    def onResponse(self, request, response):
        pass

    def onServerDown(self):
        self._is_alive = False
        self._manager.on_server_down()

    def initialize(self):
        rr = self._rpcclient.sendRequest(Initialize_REQUEST, {
            'processId': os.getpid(),
            'rootUri': 'file://' + os.getcwd(),
            'capabilities': {},
            'trace': 'off'
        })
        log.info('clangd connected with piped fd')
        log.info('clangd capabilities: %s' % rr['capabilities'])
        self._manager.on_server_connected()
        return rr

    def onInitialized(self):
        return self._rpcclient.sendNotification(Initialized_NOTIFICATION)

    def shutdown(self):
        return self._rpcclient.sendRequest(Shutdown_REQUEST, nullResponse=True)

    def exit(self):
        self._rpcclient.sendNotification(Exit_NOTIFICATION)
        self.CleanUp()

    def handleClientRequests(self):
        if not self.isAlive():
            self.onServerDown()
            return
        self._rpcclient.handleRecv()

    # notifications
    def didOpenTestDocument(self, uri, text, file_type):
        self._documents[uri] = {}
        self._documents[uri]['version'] = 1
        return self._rpcclient.sendNotification(
            DidOpenTextDocument_NOTIFICATION, {
                'textDocument': {
                    'uri': uri,
                    'languageId': file_type,
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
        for uri in list(self._documents.keys()):
            self.didCloseTestDocument(uri)

    def didCloseTestDocument(self, uri):
        if not uri in self._documents:
            return
        version = self._documents.pop(uri)['version']
        return self._rpcclient.sendNotification(
            DidCloseTextDocument_NOTIFICATION, {'textDocument': {
                'uri': uri
            }})

    def didSaveTestDocument(self, uri):
        return self._rpcclient.sendNotification(
            DidSaveTextDocument_NOTIFICATION, {'textDocument': {
                'uri': uri
            }})

    def onDiagnostics(self, uri, diagnostics):
        if not uri in self._documents:
            return
        log.info('diagnostics for %s is updated' % uri)
        self._documents[uri]['diagnostics'] = diagnostics
        pass

    def getDiagnostics(self, uri):
        self.handleClientRequests()
        if not uri in self._documents:
            return None
        if not 'diagnostics' in self._documents[uri]:
            return None
        return self._documents[uri]['diagnostics']

    def completeAt(self, uri, line, character):
        return self._rpcclient.sendRequest(Completion_REQUEST, {
            'textDocument': {
                'uri': uri,
            },
            'position': {
                'line': line,
                'character': character
            }
        })
