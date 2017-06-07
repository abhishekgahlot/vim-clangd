#!/usr/bin/env python
import glog as log
import vim, vimsupport

from time import time


class EmulateTimer:
    def __init__(self, observer, interval=5):
        self._interval = interval
        self._observer = observer

    def start(self):
        self._last_timestamp = time()

    def stop(self):
        self._last_timestamp = None

    def poll(self):
        if not self._last_timestamp:
            return
        now = time()
        if now - self._last_timestamp >= self._interval:
            self._last_timestamp = now
            self._observer.OnTimerCallback()


class EventDispatcher:
    def __init__(self, manager):
        self.manager = manager
        self._native_timer = bool(vim.eval('has("s:timer")'))
        if self._native_timer:
            log.info('vim native timer found and used')
            # FIXME use abstract timer
            self._timer = None
        else:
            self._timer = EmulateTimer(self)

    def OnVimEnter(self):
        log.debug('VimEnter')
        autostart = bool(vim.eval('g:clangd#autostart'))
        if autostart and not self.manager.isAlive():
            vimsupport.EchoText('vim-clanged is not running')
            return

        if self._timer:
            self._timer.start()

        log.info('vim-clangd plugin fully loaded')

    def OnVimLeave(self):
        log.debug('VimLeave')
        self.manager.in_shutdown = True
        if self._timer:
            self._timer.stop()
        try:
            # BufUnload won't be called at exit, you need to call it yourself
            self.manager.CloseAllFiles()
            self.manager.stopServer(confirmed=True)
        except:
            log.exception("vim-clangd plugin unload with error")
        log.info('vim-clangd plugin fully unloaded')

    def OnBufferReadPost(self, file_name):
        if self._timer:
            self._timer.poll()
        log.info('BufferReadPost %s' % file_name)

    def OnFileType(self):
        log.info('Current FileType Changed To %s' %
                 vimsupport.CurrentFileTypes()[0])
        if self._timer:
            self._timer.poll()
        self.manager.CloseCurrentFile()
        self.manager.OpenCurrentFile()
        self.manager.GetDiagnosticsForCurrentFile()

    def OnBufferWritePost(self, file_name):
        # FIXME should we use buffer_number?
        if self._timer:
            self._timer.poll()
        self.manager.SaveFile(file_name)
        log.info('BufferWritePost %s' % file_name)

    def OnBufferUnload(self, file_name):
        if self._timer:
            self._timer.poll()
        log.info('BufferUnload %s' % file_name)
        self.manager.CloseFile(file_name)

    def OnBufferDelete(self, file_name):
        if self._timer:
            self._timer.poll()
        log.info('BufferDelete %s' % file_name)
        self.manager.CloseFile(file_name)

    def OnCursorMove(self):
        if self._timer:
            self._timer.poll()
        log.debug('CursorMove')

    def OnCursorHold(self):
        if self._timer:
            self._timer.poll()
        log.debug('CursorHold')

    def OnInsertEnter(self):
        if self._timer:
            self._timer.poll()
        log.debug('InsertEnter')

    def OnInsertLeave(self):
        if self._timer:
            self._timer.poll()
        log.debug('InsertLeave')

    def OnTextChanged(self):
        if self._timer:
            self._timer.poll()
        # After a change was made to the text in the current buffer in Normal mode.
        log.debug('TextChanged')
        self.manager.UpdateCurrentBuffer()

    def OnTimerCallback(self):
        log.debug('OnTimer')
        self.manager.GetDiagnosticsForCurrentFile()
        self.manager.EchoErrorMessageForCurrentLine()
