#!/usr/bin/env python

import vimsupport, vim
from signal import signal, SIGINT, SIG_IGN
from lsp_client import LSPClient

import glog as log
import os
from os.path import dirname, abspath, join, isfile
from subprocess import check_output, CalledProcessError, Popen


def GetUriFromFilePath(file_path):
    return 'file://%s' % file_path


def GetFilePathFromUri(uri):
    return uri[7:]


def CompletionItemKind(kind):
    ##export const Text = 1;
    if kind == 1:
        return 't'
##export const Method = 2;
    elif kind == 2:
        return 'm'
##export const Function = 3;
    elif kind == 3:
        return 'f'
##export const Constructor = 4;
    elif kind == 4:
        return 'c'
##export const Field = 5;
    elif kind == 5:
        return 'f'
##export const Variable = 6;
    elif kind == 6:
        return 'v'
##export const Class = 7;
    elif kind == 7:
        return 'c'
##export const Interface = 8;
    elif kind == 8:
        return 'i'
##export const Module = 9;
    elif kind == 9:
        return 'm'
##export const Property = 10;
    elif kind == 10:
        return 'p'
##export const Unit = 11;
    elif kind == 11:
        return 'u'
##export const Value = 12;
    elif kind == 12:
        return 'v'
##export const Enum = 13;
    elif kind == 13:
        return 'e'
##export const Keyword = 14;
    elif kind == 14:
        return 'k'
##export const Snippet = 15;
    elif kind == 15:
        return 's'
##export const Color = 16;
    elif kind == 16:
        return 'c'
##export const File = 17;
    elif kind == 17:
        return 'f'
##export const Reference = 18;
    elif kind == 18:
        return 'f'
    return ''

def StartProcess(name):
    from os import pipe, devnull
    log_path = os.path.expanduser(
        vim.eval('g:clangd#log_path') + '/clangd.log')
    fdClangd = open(log_path, 'w+')
    fdInRead, fdInWrite = pipe()
    fdOutRead, fdOutWrite = pipe()
    clangd = Popen(name, stdin=fdInRead, stdout=fdOutWrite, stderr=fdClangd)
    return clangd, fdInWrite, fdOutRead, fdClangd


class ClangdManager():
    def __init__(self):
        signal(SIGINT, SIG_IGN)
        log.info('ClangdManager loaded')
        self.lined_diagnostics = {}
        self.last_completions = {}
        self.state = {}
        self._clangd = None
        self._client = None
        self._clangd_logfd = None
        autostart = bool(vim.eval('g:clangd#autostart'))
        if autostart:
            self.startServer(confirmed=True)

    def __del__(self):
        log.info('ClangdManager unloaded')

    def __str__(self):
        return 'ClangdManager'

    def isAlive(self):
        return self._clangd and self._clangd.poll(
        ) == None and self._client.isAlive()

    def startServer(self, confirmed=False):
        if self._clangd:
            log.info('clangd connected')
            vimsupport.EchoMessage(
                'clangd is connected, please stop it first!')
            return
        if confirmed or vimsupport.PresentYesOrNoDialog(
                'Should we start clangd?'):
            clangd_executable = str(vim.eval('g:clangd#clangd_executable'))
            clangd_executable = os.path.expanduser(clangd_executable)
            try:
                clangd, fdRead, fdWrite, fdClangd = StartProcess(
                    clangd_executable)
            except:
                log.exception('failed to start clangd')
                vimsupport.EchoMessage('failed to start clangd executable')
                return
            log.info('clangd started, pid %d' % clangd.pid)
            self._clangd = clangd
            self._client = LSPClient(fdRead, fdWrite)
            self._clangd_logfd = fdClangd
            self._client.initialize()
            self._client.onInitialized()

    def stopServer(self, confirmed=False):
        if confirmed or vimsupport.PresentYesOrNoDialog(
                'Should we stop clangd?'):
            try:
                self._client.shutdown()
                self._client.exit()
                if self._clangd.poll() == None:
                    self._clangd.terminate()
                if self._clangd.poll() == None:
                    self._clangd.kill()
                self._clangd_logfd.close()
                self._clangd = None
                self._client = None
                self._clangd_logfd = None
            except:
                log.exception('failed to stop clangd')
                return
            log.info('clangd stopped')

    def on_server_connected(self, wc):
        vimsupport.EchoMessage('connected with clangd daemon')
        log.info('observer: clangd connected')

    def on_server_down(self, wc):
        vimsupport.EchoMessage('lost connection with clangd daemon')
        log.info('observer: clangd down')

        self.lined_diagnostics = {}
        vimsupport.ClearClangdSyntaxMatches()
        vimsupport.UnplaceAllSigns()

    def on_bad_message_received(self, wc, message):
        log.info('observer: bad message')

    def FilterFileName(self, file_name):
        log.info('filter file %s' % file_name)
        for buf in vim.buffers:
            if buf.name == file_name:
                if buf.options['filetype'] in ['c', 'cpp', 'objc', 'objcpp']:
                    return False
                return True
        return True

    def FilterCurrentFile(self):
        file_types = vimsupport.CurrentFileTypes()
        if not file_types:
            return True
        for file_type in file_types:
            if file_type in ['c', 'cpp', 'objc', 'objcpp']:
                return False
        return True

    def OpenFile(self, file_name):
        if not self.isAlive():
            return True

        uri = GetUriFromFilePath(file_name)
        try:
            buf = vimsupport.GetBufferByName(file_name)
            file_type = buf.options['filetype'].decode('utf-8')
            text = vimsupport.ExtractUTF8Text(buf)
            self._client.didOpenTestDocument(uri, text, file_type)
        except:
            log.exception('failed to open %s' % file_name)
            vimsupport.EchoTruncatedText('unable to open %s' % file_name)
            return False

        log.info('file %s opened' % file_name)
        return True

    def OpenCurrentFile(self):
        file_name = vimsupport.CurrentBufferFileName()
        if not file_name:
            return True
        if not self.OpenFile(file_name):
            return False
        return True

    def SaveFile(self, file_name):
        if not self.isAlive():
            return True

        uri = GetUriFromFilePath(file_name)
        try:
            self._client.didSaveTestDocument(uri)
        except:
            log.exception('unable to save %s' % file_name)
            return False
        log.info('file %s saved' % file_name)
        return True

    def SaveCurrentFile(self):
        file_name = vimsupport.CurrentBufferFileName()
        if not file_name:
            return True
        return self.SaveFile(file_name)

    def CloseFile(self, file_name):
        if not self.isAlive():
            return True

        uri = GetUriFromFilePath(file_name)
        try:
            self._client.didCloseTestDocument(uri)
        except:
            log.exception('failed to close file %s' % file_name)
            return False
        log.info('file %s closed' % file_name)
        return True

    def CloseCurrentFile(self):
        file_name = vimsupport.CurrentBufferFileName()
        if not file_name:
            return True
        return self.CloseFile(file_name)

    def GetDiagnostics(self, file_name):
        if not self.isAlive():
            return []

        uri = GetUriFromFilePath(file_name)
        try:
            response = self._client.getDiagnostics(uri)
        except:
            log.exception('failed to get diagnostics %s' % file_name)
            return []
        if response is None:
            return []
        return vimsupport.ConvertDiagnosticsToQfList(file_name, response)

    def GetDiagnosticsForCurrentFile(self):
        if not self.isAlive():
            return []

        lined_diagnostics = {}
        diagnostics = self.GetDiagnostics(vimsupport.CurrentBufferFileName())
        for diagnostic in diagnostics:
            if not diagnostic['lnum'] in lined_diagnostics:
                lined_diagnostics[diagnostic['lnum']] = []
            lined_diagnostics[diagnostic['lnum']].append(diagnostic)

        # if we hit the cache, simple ignore
        if lined_diagnostics == self.lined_diagnostics:
            return diagnostics
        # clean up current diagnostics
        self.lined_diagnostics = lined_diagnostics
        vimsupport.ClearClangdSyntaxMatches()
        vimsupport.UnplaceAllSigns()

        for diagnostic in diagnostics:
            vimsupport.AddDiagnosticSyntaxMatch(
                diagnostic['lnum'],
                diagnostic['col'],
                is_error=diagnostic['severity'] >= 3)

        vimsupport.PlaceSignForErrorMessageArray(self.lined_diagnostics)
        return diagnostics

    def NearestDiagnostic(self, line, column):
        if len(self.lined_diagnostics[line]) == 1:
            return self.lined_diagnostics[line][0]

        sorted_diagnostics = sorted(
            self.lined_diagnostics[line],
            key=lambda diagnostic: abs(diagnostic['col'] - column))
        return sorted_diagnostics[0]

    def ErrorStatusForCurrentLine(self):
        if not self.isAlive():
            return ''
        current_line, current_column = vimsupport.CurrentLineAndColumn()
        if not current_line in self.lined_diagnostics:
            return ''
        diagnostic = self.NearestDiagnostic(current_line, current_column)
        serverity_strings = [
            'ignored',
            'note',
            'warning',
            'error',
            'fatal',
        ]
        return serverity_strings[int(diagnostic['severity'])]

    def EchoErrorMessageForCurrentLine(self):
        vimsupport.EchoText('')
        if not self.isAlive():
            return
        current_line, current_column = vimsupport.CurrentLineAndColumn()
        if not current_line in self.lined_diagnostics:
            return ''
        diagnostic = self.NearestDiagnostic(current_line, current_column)
        vimsupport.EchoTruncatedText(diagnostic['text'])

    def EchoDetailedErrorMessage(self):
        if not self.isAlive():
            return
        current_line, _ = vimsupport.CurrentLineAndColumn()
        if not current_line in self.lined_diagnostics:
            return
        full_text = ''
        for diagnostic in self.lined_diagnostics[current_line]:
            full_text += 'L%d:C%d %s\n' % (diagnostic['lnum'],
                                           diagnostic['col'],
                                           diagnostic['text'])
        vimsupport.EchoText(full_text[:-1])

    def UpdateSpecifiedBuffer(self, buf):
        if not self.isAlive():
            return
        # FIME we need to add a temp name for every unamed buf?
        if not buf.name:
            return
        if not buf.options['modified']:
            if (len(buf) > 1) or (len(buf) == 1 and len(buf[0])):
                return
        textbody = vimsupport.ExtractUTF8Text(buf)
        # we need to solve this
        uri = GetUriFromFilePath(buf.name)
        self._client.didChangeTestDocument(uri, textbody)

    def UpdateCurrentBuffer(self):
        if not self.isAlive():
            return
        buf = vimsupport.CurrentBuffer()
        try:
            self.UpdateSpecifiedBuffer(buf)
        except:
            log.exception('failed to update curent buffer')
            vimsupport.EchoTruncatedText('unable to update curent buffer')


    def CalculateStartColumn(self):
        current_line = vimsupport.CurrentLine()
        _, column = vimsupport.CurrentLineAndColumn()
        start_column = min(column, len(current_line))
        start_column -= 1
        while start_column:
            c = current_line[start_column - 1]
            if not (str.isalnum(c) or c == '_'):
                break
            start_column -= 1
        return start_column, current_line[start_column:column]

    def CodeCompleteAtCurrent(self):
        if not self.isAlive():
            return -2

        line, column = vimsupport.CurrentLineAndColumn()
        log.debug('code complete at %d:%d' % (line, column))
        self.last_completions = {}
        start_column, word = self.CalculateStartColumn()
        uri = GetUriFromFilePath(vimsupport.CurrentBufferFileName())
        try:
            completions = self._client.completeAt(uri, line - 1, column - 1)
        except:
            log.exception('failed to code complete at %d:%d' % (line, column))
            return -2
        words = []
        total_cnt = len(completions)
        if word == '':
            completions = sorted(
                completions, key=lambda completion: completion['kind'] if 'kind' in completion else 1)
            completions = completions[0:20]
        else:
            completions = list(
                filter(lambda completion: completion['label'].startswith(word),
                       completions))
        log.info('%d completions in total, reduced to %d' % (total_cnt, len(completions)))
        for completion in completions:
            if not 'kind' in completion:
                completion['kind'] = 1
            if not 'documentation' in completion:
                completion['documentation'] = completion['label']
            words.append({
                'word': completion['label'], # The actual completion
                'kind': CompletionItemKind(completion['kind']), # The type of completion, one character
                'info': completion['documentation'],  #document
                'icase': 1, # ignore case
                'dup': 1 # allow duplicates
            })
        self.last_completions = words
        return start_column + 1

    def GetCompletions(self):
        if len(self.last_completions) == 0:
            return {'words': [], 'refresh': 'always'}
        _, column = vimsupport.CurrentLineAndColumn()
        words = self.last_completions
        size = len(words)
        if size > 20:
            size = 20
        return {'words': words[0:size], 'refresh': 'always'}

    def GotoDefinition(self):
        if not self.isAlive():
            return

        line, column = vimsupport.CurrentLineAndColumn()
        #TODO we may want to reparse source file actively here or by-pass the
        # reparsing to incoming source file monitor?

        response = self.wc.GetDefinition(vimsupport.CurrentBufferFileName(),
                                         line, column)
        if not response:
            log.warning('unable to get definition at %d:%d' % (line, column))
            vimsupport.EchoTruncatedText('unable to get definition at %d:%d' %
                                         (line, column))
            return
        location = response.location
        file_name = location.file_name
        line = location.line
        column = location.column
        vimsupport.GotoBuffer(file_name, line, column)

    def ShowCursorDetail(self):
        if not self.isAlive():
            return

        line, column = vimsupport.CurrentLineAndColumn()
        #TODO we may want to reparse source file actively here or by-pass the
        # reparsing to incoming source file monitor?
        response = self.wc.GetCursorDetail(vimsupport.CurrentBufferFileName(),
                                           line, column)
        if not response:
            vimsupport.EchoTruncatedText('unable to get cursor at %d:%d' %
                                         (line, column))
            log.warning('unable to get cursor at %d:%d' % (line, column))
            return
        detail = response.detail
        message = 'Type: %s Kind: %s' % (detail.type, detail.kind)
        brief_comment = detail.brief_comment
        if brief_comment:
            message += '   '
            message += brief_comment
        vimsupport.EchoText(message)

    def CloseAllFiles(self):
        if not self.isAlive():
            return
        try:
            self._client.closeAllFiles()
        except:
            log.exception('failed to close all files')
