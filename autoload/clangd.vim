let s:save_cpo = &cpo
set cpo&vim

fu! s:restore_cpo()
  let &cpo = s:save_cpo
  unlet s:save_cpo
endf

let s:script_folder_path = escape(expand('<sfile>:p:h'), '\')
let s:old_cursor_position = []
let s:omnifunc_mode = 0
let s:cursor_moved = 0

" Main Entrance
fu! clangd#Enable()
  if &diff
    return
  endif
  call s:SetUpFirstRun()
  try
    call s:SetUpPython()
  catch /.*/
    if v:exception != ""
        echoerr 'failed to initialize clangd plugin, ' v:exception
        return
    endif
  endtry
  call s:TurnOffSyntasticForCFamily()
  call s:SetUpSyntasticSigns()
  call s:SetUpSyntasticHl()
  augroup clangd
    autocmd!
    "autocmd TabEnter *
    autocmd VimLeave * call s:VimLeave()
    autocmd BufReadPost * call s:BufferReadPost(expand('<afile>:p'))
    autocmd FileType * call s:FileType()
    autocmd BufWritePost * call s:BufferWritePost(expand('<afile>:p'))
    autocmd BufUnload * call s:BufferUnload(expand('<afile>:p'))
    autocmd BufDelete * call s:BufferDelete(expand('<afile>:p'))
    autocmd CursorMoved * call s:CursorMove()
    autocmd CursorMovedI * call s:CursorMoveInsertMode()
    autocmd CursorHold,CursorHoldI * call s:CursorHold()
    autocmd InsertEnter * call s:InsertEnter()
    autocmd InsertLeave * call s:InsertLeave()
    autocmd TextChanged,TextChangedI * call s:TextChanged()
  augroup END
  call s:VimEnter()
endf

" Sub Entrances
fu! s:SetUpPython() abort
  py import sys
  exe 'python sys.path.insert(0, "' . s:script_folder_path . '/../python")'
python << endpython
from vimsupport import EchoMessage
import vim
try:
  import glog as log
  log_level = str(vim.eval('g:clangd#log_level'))
  log_path = str(vim.eval('g:clangd#log_path')) + '/vim-clangd.log'
  log.init(log_level, log_path)
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
endpython
endf

fu! s:TurnOffSyntasticForCFamily()
  let g:syntastic_cpp_checkers = []
  let g:syntastic_c_checkers = []
  let g:syntastic_objc_checkers = []
  let g:syntastic_objcpp_checkers = []
endf

fu! s:SetUpSyntasticSigns()
  if !hlexists('clangdErrorSign')
    if hlexists('SyntasticErrorSign')
      highlight link clangdErrorSign SyntasticErrorSign
    else
      highlight link clangdErrorSign error
    endif
  endif

  if !hlexists('clangdWarningSign')
    if hlexists('SyntasticWarningSign')
      highlight link clangdWarningSign SyntasticWarningSign
    else
      highlight link clangdWarningSign todo
    endif
  endif

  if !hlexists('clangdErrorLine')
    highlight link clangdErrorLine SyntasticErrorLine
  endif

  if !hlexists('clangdWarningLine')
    highlight link clangdWarningLine SyntasticWarningLine
  endif

  let l:error_symbol = get(g:, 'syntastic_error_symbol', '>>')
  let l:warning_symbol = get(g:, 'syntastic_warning_symbol', '>>')
  exe 'sign define clangdError text=' . l:error_symbol .
        \ ' texthl=clangdErrorSign linehl=clangdErrorLine'
  exe 'sign define clangdWarning text=' . l:warning_symbol .
        \ ' texthl=clangdWarningSign linehl=clangdWarningLine'
endf


fu! s:SetUpSyntasticHl()
  if !hlexists('clangdErrorSection')
    if hlexists('SyntasticError')
      highlight link clangdErrorSection SyntasticError
    else
      highlight link clangdErrorSection SpellBad
    endif
  endif

  if !hlexists('clangdWarningSection')
    if hlexists('SyntasticWarning')
      highlight link clangdWarningSection SyntasticWarning
    else
      highlight link clangdWarningSection SpellCap
    endif
  endif
endf

fu! s:SetUpFirstRun()
    if !exists('g:clangd#clangd_executable')
       let g:clangd#clangd_executable = 'clangd'
    endif
    if !exists('g:clangd#popup_auto')
       let g:clangd#popup_auto = 1
    endif
    if !exists('g:clangd#autostart')
       let g:clangd#autostart = 1
    endif
    if !exists('g:clangd#log_level')
       let g:clangd#log_level = 'warn'
    endif
    if !exists('g:clangd#log_path')
       let g:clangd#log_path = '~/.config/clangd/logs/'
    endif
endf

" Watchers

fu! s:VimEnter()
  py handler.OnVimEnter()
  " fix a bug it won't call buffer enter the very first file
  call s:FileType()
endf

fu! s:VimLeave()
  py handler.OnVimLeave()
endf

fu! s:BufferRead()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  py handler.OnBufferRead()
endf

fu! s:BufferReadPost(file_name)
  if pyeval("manager.FilterFileName(vim.eval('a:file_name'))")
    return
  endif
  py handler.OnBufferReadPost(vim.eval('a:file_name'))
endf

fu! s:FileType()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  call s:SetCompletionCallback()
  py handler.OnFileType()
endf

fu! s:BufferWritePost(file_name)
  if pyeval("manager.FilterFileName(vim.eval('a:file_name'))")
    return
  endif
  py handler.OnBufferWritePost(vim.eval('a:file_name'))
endf

fu! s:BufferUnload(file_name)
  if pyeval("manager.FilterFileName(vim.eval('a:file_name'))")
    return
  endif
  py handler.OnBufferUnload(vim.eval('a:file_name'))
endf

fu! s:BufferDelete(file_name)
  if pyeval("manager.FilterFileName(vim.eval('a:file_name'))")
    return
  endif
  py handler.OnBufferDelete(vim.eval('a:file_name'))
endf

fu! s:CursorMove()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  let current_position = getpos('.')
  let s:cursor_moved = current_position != s:old_cursor_position
  py handler.OnCursorMove()
  let s:old_cursor_position = current_position
endf

fu! s:CursorMoveInsertMode()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  call s:CursorMove()
  call s:InvokeCompletion()
endf

fu! s:CursorHold()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  py handler.OnCursorHold()
endf

fu! s:InsertEnter()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  let s:old_cursor_position = []
  let s:omnifunc_mode = 0
  py handler.OnInsertEnter()
endf

fu! s:InsertLeave()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  py handler.OnInsertLeave()
endf

fu! s:TextChanged()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  py handler.OnTextChanged()
endf

" Helpers

fu! s:ShowDiagnostics()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  let diags = pyeval('manager.GetDiagnosticsForCurrentFile()')
  if !empty(diags)
    call setloclist(0, diags)

    lopen
  else
    echom "No warnings or errors detected"
  endif
endf

fu! s:ForceCompile()
  if pyeval('manager.FilterCurrentFile()')
    return
  endif
  py manager.ReparseCurrentFile()
  py manager.GetDiagnosticsForCurrentFile()
  py manager.EchoErrorMessageForCurrentLine()
endf

fu! clangd#CodeCompleteAt(findstart, base)
  if s:omnifunc_mode
    return clangd#OmniCompleteAt(a:findstart, a:base)
  endif
  if a:findstart
    if pyeval('manager.FilterCurrentFile()')
      return -3
    endif
    if !s:cursor_moved
      return -2
    endif
    if !pyeval('manager.isAlive()')
      return -2
    endif
    let l:column = pyeval('manager.CodeCompleteAtCurrent()')
    return l:column - 1
  endif

  if pyeval('manager.FilterCurrentFile()')
    return []
  endif
  " return completions
  let l:completions = pyeval('manager.GetCompletions()')
  " Report a result.
  if complete_check()
    return []
  endif
  return l:completions
endf

fu! clangd#OmniCompleteAt(findstart, base)
  if a:findstart
    if !pyeval('manager.isAlive()')
      return -2
    endif
    let s:omnifunc_mode = 1
    let l:column = pyeval('manager.CodeCompleteAtCurrent()')
    return l:column
  endif

  " return completions
  let l:completions = pyeval('manager.GetCompletions()')
  return l:completions
endf

fu! s:InvokeCompletion()
  if &completefunc != "clangd#CodeCompleteAt"
    return
  endif
  let is_blank = pyeval('not vim.current.line or vim.current.line.isspace()')
  if is_blank
    return
  endif

  if !s:cursor_moved
    return
  endif
  call feedkeys("\<C-X>\<C-U>\<C-P>", 'n')
endf

fu! s:SetCompletionCallback()
  if !g:clangd#popup_auto
    return
  endif
  set completeopt-=menu
  set completeopt+=menuone
  set completeopt-=longest
  let &l:completefunc = 'clangd#CodeCompleteAt'
  " let &l:omnifunc = 'clangd#OmniCompleteAt'
endf

fu! s:GotoDefinition()
  if pyeval('manager.FilterCurrentFile()')
    echom 'unsupported file type'
    return
  endif

  py manager.GotoDefinition()
endf

fu! s:ShowDetailedDiagnostic()
  if pyeval('manager.FilterCurrentFile()')
    echom 'unsupported file type'
    return
  endif

  py manager.EchoDetailedErrorMessage()
endf

fu! s:ShowCursorDetail()
  if pyeval('manager.FilterCurrentFile()')
    echom 'unsupported file type'
    return
  endif

  py manager.ShowCursorDetail()
endf

fu! s:StartServer()
  py manager.startServer(confirmed = True)
endf

fu! s:StopServer()
  py manager.stopServer(confirmed = True)
endf

fu! s:RestartServer()
  py manager.stopServer(confirmed = True)
  py manager.startServer(confirmed = True)
endf

fu! ClangdStatuslineFlag()
  if pyeval('manager.FilterCurrentFile()')
    return ''
  endif
  return pyeval('manager.ErrorStatusForCurrentLine()')
endf

" Setup Commands
command! ClangdCodeComplete call feedkeys("\<C-X>\<C-U>\<C-P>", 'n')
command! ClangdDiags call s:ShowDiagnostics()
command! ClangdShowDetailedDiagnostic call s:ShowDetailedDiagnostic()
command! ClangdForceCompile call s:ForceCompile()
" command! ClangdGotoDefinition call s:GotoDefinition()
" command! ClangdShowCursorDetail call s:ShowCursorDetail()
command! ClangdStartServer call s:StartServer()
command! ClangdStopServer call s:StopServer()
command! ClangdRestartServer call s:RestartServer()

call s:restore_cpo()
