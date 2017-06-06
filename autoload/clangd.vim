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
  Python import sys, vim
  Python sys.path.insert(0, vim.eval('s:script_folder_path') + '/../python')
  Python from loader import manager, handler
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
       let clangd_path = s:script_folder_path . '/../script/clangd'
       if filereadable(clangd_path)
            let g:clangd#clangd_executable = clangd_path
       else
            let g:clangd#clangd_executable = 'clangd'
       endif
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
    if !exists('g:clangd#py_version')
       if has('python3')
          let g:clangd#py_version = 3
       else
          let g:clangd#py_version = 2
       endif
    endif
    if g:clangd#py_version == 3
        let s:python_version = 3
        let cmd_exec = 'python3'
    else
        let s:python_version = 2
        let cmd_exec = 'python'
    endif
    exe 'command! -nargs=1 Python '.cmd_exec.' <args>'
endf

" Watchers

fu! s:VimEnter()
  Python handler.OnVimEnter()
  " fix a bug it won't call buffer enter the very first file
  call s:FileType()
  func
  if has('timers')
      fu! OnTimerCallback(timer)
        Python handler.OnTimerCallback()
      endf
      let s:timer = timer_start(5000, 'OnTimerCallback', { 'repeat': -1 })
  endif
endf

fu! s:VimLeave()
  if has('timers')
      exec timer_stop(s:timer)
  endif
  Python handler.OnVimLeave()
endf

fu! s:BufferRead()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  Python handler.OnBufferRead()
endf

fu! s:BufferReadPost(file_name)
  if s:PyEval('manager.FilterFileName("'. a:file_name . '")')
    return
  endif
  Python handler.OnBufferReadPost(vim.eval('a:file_name'))
endf

fu! s:FileType()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  call s:SetCompletionCallback()
  Python handler.OnFileType()
endf

fu! s:BufferWritePost(file_name)
  if s:PyEval('manager.FilterFileName("'. a:file_name . '")')
    return
  endif
  Python handler.OnBufferWritePost(vim.eval('a:file_name'))
endf

fu! s:BufferUnload(file_name)
  if s:PyEval('manager.FilterFileName("'. a:file_name . '")')
    return
  endif
  Python handler.OnBufferUnload(vim.eval('a:file_name'))
endf

fu! s:BufferDelete(file_name)
  if s:PyEval('manager.FilterFileName("'. a:file_name . '")')
    return
  endif
  Python handler.OnBufferDelete(vim.eval('a:file_name'))
endf

fu! s:CursorMove()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  let current_position = getpos('.')
  let s:cursor_moved = current_position != s:old_cursor_position
  Python handler.OnCursorMove()
  let s:old_cursor_position = current_position
endf

fu! s:CursorMoveInsertMode()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  call s:CursorMove()
  call s:InvokeCompletion()
endf

fu! s:CursorHold()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  Python handler.OnCursorHold()
endf

fu! s:InsertEnter()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  let s:old_cursor_position = []
  let s:omnifunc_mode = 0
  Python handler.OnInsertEnter()
endf

fu! s:InsertLeave()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  Python handler.OnInsertLeave()
endf

fu! s:TextChanged()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  Python handler.OnTextChanged()
endf

" Helpers

fu! s:ShowDiagnostics()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  let diags = s:PyEval('manager.GetDiagnosticsForCurrentFile()')
  if !empty(diags)
    call setloclist(0, diags)

    lopen
  else
    echom "No warnings or errors detected"
  endif
endf

fu! s:ForceCompile()
  if s:PyEval('manager.FilterCurrentFile()')
    return
  endif
  Python manager.ReparseCurrentFile()
  Python manager.GetDiagnosticsForCurrentFile()
  Python manager.EchoErrorMessageForCurrentLine()
endf

fu! clangd#CodeCompleteAt(findstart, base)
  if s:omnifunc_mode
    return clangd#OmniCompleteAt(a:findstart, a:base)
  endif
  if a:findstart
    if s:PyEval('manager.FilterCurrentFile()')
      return -3
    endif
    if !s:cursor_moved
      return -2
    endif
    if !s:PyEval('manager.isAlive()')
      return -2
    endif
    let l:column = s:PyEval('manager.CodeCompleteAtCurrent()')
    return l:column - 1
  endif

  if s:PyEval('manager.FilterCurrentFile()')
    return []
  endif
  " return completions
  let l:completions = s:PyEval('manager.GetCompletions()')
  " Report a result.
  if complete_check()
    return []
  endif
  return l:completions
endf

fu! clangd#OmniCompleteAt(findstart, base)
  if a:findstart
    if !s:PyEval('manager.isAlive()')
      return -2
    endif
    let s:omnifunc_mode = 1
    let l:column = s:PyEval('manager.CodeCompleteAtCurrent()')
    return l:column
  endif

  " return completions
  let l:completions = s:PyEval('manager.GetCompletions()')
  return l:completions
endf

fu! s:InvokeCompletion()
  if &completefunc != "clangd#CodeCompleteAt"
    return
  endif
  let is_blank = s:PyEval('not vim.current.line or vim.current.line.isspace()')
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
  if s:PyEval('manager.FilterCurrentFile()')
    echom 'unsupported file type'
    return
  endif

  Python manager.GotoDefinition()
endf

fu! s:ShowDetailedDiagnostic()
  if s:PyEval('manager.FilterCurrentFile()')
    echom 'unsupported file type'
    return
  endif

  Python manager.EchoDetailedErrorMessage()
endf

fu! s:ShowCursorDetail()
  if s:PyEval('manager.FilterCurrentFile()')
    echom 'unsupported file type'
    return
  endif

  Python manager.ShowCursorDetail()
endf

fu! s:StartServer()
  Python manager.startServer(confirmed = True)
endf

fu! s:StopServer()
  Python manager.stopServer(confirmed = True)
endf

fu! s:RestartServer()
  Python manager.stopServer(confirmed = True)
  Python manager.startServer(confirmed = True)
endf

fu! s:PyEval(line)
    if s:python_version == 3
        return py3eval(a:line)
    else
        return pyeval(a:line)
    endif
endf

fu! ClangdStatuslineFlag()
  if s:PyEval('manager.FilterCurrentFile()')
    return ''
  endif
  return s:PyEval('manager.ErrorStatusForCurrentLine()')
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
