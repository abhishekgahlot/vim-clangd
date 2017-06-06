#!/usr/bin/env python
import glog as log
import vim, vimsupport


class EventDispatcher:
    def __init__(self, manager):
        self.manager = manager
        self._emulate_timer = not bool(vim.eval('has("timers")'))

    def OnVimEnter(self):
        log.debug('VimEnter')
        autostart = bool(vim.eval('g:clangd#autostart'))
        if autostart and not self.manager.isAlive():
            vimsupport.EchoText('vim-clanged is not running')
            return

        log.info('vim-clangd plugin fully loaded')

    def OnVimLeave(self):
        log.debug('VimLeave')
        self.manager.in_shutdown = True
        try:
            # BufUnload won't be called at exit, you need to call it yourself
            self.manager.CloseAllFiles()
            self.manager.stopServer(confirmed=True)
        except:
            log.exception("vim-clangd plugin unload with error")
        log.info('vim-clangd plugin fully unloaded')

    def OnBufferReadPost(self, file_name):
        log.info('BufferReadPost %s' % file_name)

    def OnFileType(self):
        log.info('Current FileType Changed To %s' %
                 vimsupport.CurrentFileTypes()[0])
        self.manager.CloseCurrentFile()
        self.manager.OpenCurrentFile()
        self.manager.GetDiagnosticsForCurrentFile()

    def OnBufferWritePost(self, file_name):
        # FIXME should we use buffer_number?
        self.manager.SaveFile(file_name)
        log.info('BufferWritePost %s' % file_name)

    def OnBufferUnload(self, file_name):
        log.info('BufferUnload %s' % file_name)
        self.manager.CloseFile(file_name)

    def OnBufferDelete(self, file_name):
        log.info('BufferDelete %s' % file_name)
        self.manager.CloseFile(file_name)

    def OnCursorMove(self):
        log.debug('CursorMove')
        if self._emulate_timer:
            self.OnTimer()

    def OnCursorHold(self):
        log.debug('CursorHold')
        if self._emulate_timer:
            self.OnTimer()

    def OnInsertEnter(self):
        log.debug('InsertEnter')

    def OnInsertLeave(self):
        log.debug('InsertLeave')

    def OnTextChanged(self):
        # After a change was made to the text in the current buffer in Normal mode.
        log.debug('TextChanged')
        self.manager.UpdateCurrentBuffer()

    def OnTimerCallback(self):
        log.debug('OnTimer')
        self.manager.GetDiagnosticsForCurrentFile()
        self.manager.EchoErrorMessageForCurrentLine()
