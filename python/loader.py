from vimsupport import EchoMessage
import vim
import os

try:
  import glog as log
  log_level = str(vim.eval('g:clangd#log_level'))
  log_path = os.path.expanduser(str(vim.eval('g:clangd#log_path')))
  if not os.path.exists(log_path):
      os.makedirs(log_path)
  log.init(log_level, log_path + '/vim-clangd.log')
except Exception as e:
  EchoMessage(str(e))
  raise

try:
  from clangd_manager import ClangdManager
  from event_dispatcher import EventDispatcher
  manager = ClangdManager()
  handler = EventDispatcher(manager)
except Exception as e:
  EchoMessage(str(e))
  log.exception(e)
  raise
