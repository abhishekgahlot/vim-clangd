## vim-clangd
[![Build Status](https://travis-ci.org/Chilledheart/vim-clangd.svg?branch=master)](http://travis-ci.org/Chilledheart/vim-clangd)

## Features

|C/C++ Editor feature                |Clangd    |vim-clangd|
|------------------------------------|----------|----------|
|Formatting                          |Yes       |No        |
|Completion                          |Yes       |Yes       |
|Diagnostics                         |Yes       |Yes       |
|Fix-its                             |Yes       |No        |
|Go to Definition                    |No        |No        |
|Source hover                        |No        |No        |
|Signature Help                      |No        |No        |
|Find References                     |No        |No        |
|Document Highlights                 |No        |No        |
|Rename                              |No        |No        |
|Code Lens                           |No        |No        |
|Syntax and Semantic Coloring        |No        |No        |
|Code folding                        |No        |No        |
|Call hierarchy                      |No        |No        |
|Type hierarchy                      |No        |No        |
|Organize Includes                   |No        |No        |
|Quick Assist                        |No        |No        |
|Extract Local Variable              |No        |No        |
|Extract Function/Method             |No        |No        |
|Hide Method                         |No        |No        |
|Implement Method                    |No        |No        |
|Gen. Getters/Setters                |No        |No        |

## How to use vim-clangd plugins

1. use vunble or other vim plugin manager to add vim-clangd in vimrc file
such as
```
Plugin 'Chilledheart/vim-clangd'
```

2. setup clangd
you can do it by run this script
```
./script/build-clangd.sh
```
vim-clangd will search builtin clangd and then fallback to clangd in the path.
however there is no simple way to get a binary clangd yet including llvm
official apt repo.

ubuntu distribution, you can refer to [docker/Dockerfile.xenial](https://github.com/Chilledheart/vim-clangd/blob/master/docker/Dockerfile.xenial) as well.

see more at [clang docs](https://clang.llvm.org/get_started.html) but "extra Clang tools" is not optional.

3. start vim and enjoy

## Advanced Usage

### Specify other clangd instance
if you have many clangd instances and want to specify one,
you can write clangd's path in vimrc file such as
```
let g:clangd#clangd_executable = '~/build-llvm/bin/clangd'
```

### Turn off auto completion
Sometimes completion is slow. there is a way to turn it off.

Put this in your vimrc file
```
let g:clangd#popup_auto = 0
```

### Specify python version
vim-clangd will recognize your builtin python support of vim and
will choose python3 as default.

you might want to specify python version forcely

```
let g:clangd#py_version = 2
```
this will force vim-clangd to use python2
