## vim-clangd
[![Build Status](https://travis-ci.org/Chilledheart/vim-clangd.svg?branch=master)](http://travis-ci.org/Chilledheart/vim-clangd)

# Features

|C/C++ Editor feature                |Clangd    |vim-clangd|
|------------------------------------|----------|----------|
|Formatting                          |Yes       |No        |
|Completion                          |Yes       |Yes       |
|Diagnostics                         |Yes       |Yes       |
|Fix-its                             |No        |No        |
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

# How to use vim-clangd plugins

1. use vunble or other vim plugin manager to add vim-clangd in vimrc file
such as
```
Plugin 'Chilledheart/vim-clangd'
```

2. build clangd manually and specify clangd's path in vimrc file
such as
```
let g:clangd#clangd_executable = '~/build-llvm/bin/clangd'
```

3. start vim and enjoy

### How to build clangd

see more at [clang docs](https://clang.llvm.org/get_started.html) but "extra Clang tools" is not optional.
