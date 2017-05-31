#!/usr/bin/env python
import vim
import os
import glog as log


# Given an object, returns a str object that's utf-8 encoded.
def ToUtf8IfNeeded(value):
    if isinstance(value, unicode):
        return value.encode('utf8')
    if isinstance(value, str):
        return value
    return str(value)


def PresentYesOrNoDialog(message):
    return int(vim.eval('confirm("%s", "&Yes\n&No")' % message)) == 1


def CurrentLineAndColumn():
    """Returns the 0-based current line and 0-based current column."""
    # See the comment in CurrentColumn about the calculation for the line and
    # column number
    line, column = vim.current.window.cursor
    return line, column + 1


def CurrentLine():
    return vim.current.line


def CurrentBuffer():
    return vim.current.buffer


def CurrentBufferFileName():
    file_name = vim.current.buffer.name
    if file_name == None:
        EchoMessage('empty buffer name')
    return file_name


def CurrentFileTypes():
    return vim.eval("&filetype").split('.')

def GetBufferByName(file_name):
    for buf in vim.buffers:
        if buf.name == file_name:
            return buf
    return None

def ExtractUTF8Text(buf):
    enc = buf.options['fileencoding']
    if enc:
        decoded_textbody = []
        for chunk in buf:
            decoded_textbody.append(chunk.decode(enc))
        decoded_textbody = u'\n'.join(decoded_textbody)
    else:
        decoded_textbody = '\n'.join(buf).decode('utf-8')
    textbody = decoded_textbody.encode('utf-8')
    return textbody

#TODO refine this
def EscapeForVim(text):
    return text.replace("'", "''")


def FiletypesForBuffer(buffer_object):
    # NOTE: Getting &ft for other buffers only works when the buffer has been
    # visited by the user at least once, which is true for modified buffers
    return GetBufferOption(buffer_object, 'ft').split('.')


def GetBufferOption(buffer_object, option):
    to_eval = 'getbufvar({0}, "&{1}")'.format(buffer_object.number, option)
    return GetVariableValue(to_eval)


def GetVariableValue(variable):
    return vim.eval(variable)


def GetBoolValue(variable):
    return bool(int(vim.eval(variable)))


def GetIntValue(variable):
    return int(vim.eval(variable))


def GetBufferNumberForFilename(filename, open_file_if_needed=True):
    return GetIntValue(u"bufnr('{0}', {1})".format(
        EscapeForVim(os.path.realpath(filename)), int(open_file_if_needed)))


# clean all signs for existing buffer
# FIXME clean clangdSigns only
def UnplaceAllSigns():
    buffer_num = vim.current.buffer.number
    vim.command('sign unplace * buffer=%d' % buffer_num)


def PlaceSignForErrorMessage(buffer_num, index, diagnostic):
    if diagnostic['severity'] >= 3:
        sign_name = 'clangdError'
    else:
        sign_name = 'clangdWarning'

    try:
        vim.command('sign place %d line=%d name=%s buffer=%d' %
                    (index, diagnostic['lnum'], sign_name, buffer_num))
    except:
        log.exception('sign place %d line=%d name=%s buffer=%d' %
                    (index, diagnostic['lnum'], sign_name, buffer_num))


def PlaceSignForErrorMessageArray(diagnostics):
    buffer_num = vim.current.buffer.number

    index = 1
    for line_num in diagnostics:
        # FIXME we should show most severity error
        PlaceSignForErrorMessage(buffer_num, index, diagnostics[line_num][0])
        index += 1


def ConvertDiagnosticsToQfList(file_name, diagnostics):
    retval = []
    for diagnostic in diagnostics:
        location = diagnostic['range']['start']
        line = location['line'] + 1
        column = location['character']
        severity = diagnostic['severity']
        msg = diagnostic['message']

        # when the error is "too many error occurs"
        if line == 0 and column == 0:
            continue

        retval.append({
            'bufnr': GetBufferNumberForFilename(file_name),
            'lnum': line,
            'col': column,
            'text': ToUtf8IfNeeded(msg),
            'full_text': ToUtf8IfNeeded(msg),
            'type': 1,
            'valid': 1,
            'severity': severity
        })

    return retval


def EchoMessage(text):
    for line in str(text).split('\n'):
        vim.command('{0} \'{1}\''.format('echom', EscapeForVim(line)))


def EchoText(text):
    for line in str(text).split('\n'):
        vim.command('{0} \'{1}\''.format('echo', EscapeForVim(line)))


def EchoTextH(text):
    for line in str(text).split('\n'):
        vim.command('{0} \'{1}\''.format('echoh', EscapeForVim(line)))


def EchoTruncatedText(text):
    width = int(vim.eval('&columns')) - 3
    if width <= 0:
        return
    saved_ruler = vim.eval('&ruler')
    saved_showcmd = vim.eval('&showcmd')
    vim.command('set noruler noshowcmd')

    truncated = str(text)[:width]
    EchoText(truncated)

    saved_ruler = vim.eval('&ruler')
    saved_showcmd = vim.eval('&showcmd')
    vim.command('let &ruler = %s' % saved_ruler)
    vim.command('let &showcmd = %s' % saved_showcmd)


def ClearClangdSyntaxMatches():
    matches = vim.eval('getmatches()')
    for match in matches:
        if match['group'].startswith('clangd'):
            vim.eval('matchdelete({0})'.format(match['id']))


def AddDiagnosticSyntaxMatch(line_num,
                             column_num,
                             line_end_num=None,
                             column_end_num=None,
                             is_error=True):
    group = 'clangdErrorSection' if is_error else 'clangdWarningSection'

    if not line_end_num:
        line_end_num = line_num

    line_num, column_num = LineAndColumnNumbersClamped(line_num, column_num)
    line_end_num, column_end_num = LineAndColumnNumbersClamped(
        line_end_num, column_end_num)

    if not column_end_num:
        return GetIntValue("matchadd('{0}', '\%{1}l\%{2}c')".format(
            group, line_num, column_num))
    else:
        return GetIntValue(
            "matchadd('{0}', '\%{1}l\%{2}c\_.\\{{-}}\%{3}l\%{4}c')".format(
                group, line_num, column_num, line_end_num, column_end_num))


def LineAndColumnNumbersClamped(line_num, column_num):
    new_line_num = line_num
    new_column_num = column_num

    max_line = len(vim.current.buffer)
    if line_num and line_num > max_line:
        new_line_num = max_line

    max_column = len(vim.current.buffer[new_line_num - 1])
    if column_num and column_num > max_column:
        new_column_num = max_column

    return new_line_num, new_column_num


def GotoOpenedBuffer(filename, line, column):
    filepath = os.path.realpath(filename)

    for tab in vim.tabpages:
        for win in tab.windows:
            if win.buffer.name == filepath:
                vim.current.tabpage = tab
                vim.current.window = win
                vim.current.window.cursor = (line, column - 1)

                # Center the screen on the jumped-to location
                vim.command('normal! zz')
                return True

    return False


def GotoBuffer(filename, line, column):
    # Add an entry to the jumplist
    vim.command("normal! m'")

    if filename != CurrentBufferFileName():
        if GotoOpenedBuffer(filename, line, column):
            return

        buf = vim.current.buffer
        usable = not buf.options['modified'] or buf.options['bufhidden']
        if usable:
            command = 'edit'
        else:
            command = 'split'
        vim.command(
            'keepjumps {0} {1}'.format(command, filename.replace(' ', r'\ ')))
    vim.current.window.cursor = (line, column - 1)

    # Center the screen on the jumped-to location
    vim.command('normal! zz')
