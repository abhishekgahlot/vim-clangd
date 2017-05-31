if exists("g:loaded_clangd")
  finish
endif

let g:loaded_clangd = 1
let s:save_cpo = &cpo
set cpo&vim

fu! s:restore_cpo()
  let &cpo = s:save_cpo
  unlet s:save_cpo
endf

if v:version < 704
  echomsg "requires Vim 7.4 or later"
  call s:restore_cpo()
  finish
elseif !has('python')
  echomsg "requires Python2 support"
  call s:restore_cpo()
  finish
endif

augroup clangdStart
  autocmd!
  autocmd VimEnter * call clangd#Enable()
augroup END

call s:restore_cpo()
