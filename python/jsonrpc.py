# simple jsonrpc client over raw socket
# https://github.com/Microsoft/language-server-protocol/blob/master/protocol.md
# Content-Length: ...\r\n
# \r\n
# {
#   'jsonrpc': '2.0',
#     'id': 1,
#       'method': 'textDocument/didOpen',
#         'params': {
#             ...
#               }
#               }
#
import json, os
import glog as log
from timeout import timeout
from errno import EINTR


def EstimateUnreadBytes(fd):
    from array import array
    from fcntl import ioctl
    from termios import FIONREAD
    buf = array('i', [0])
    ioctl(fd, FIONREAD, buf, 1)
    return buf[0]

@timeout(5)
def write_utf8(fd, data):
    msg = data.encode('utf-8')
    while len(msg):
        try:
            written = os.write(fd, msg)
            msg = msg[written:]
        except OSError,e:
          if e.errno != EINTR:
              raise
    return msg

@timeout(5)
def read_utf8(fd, length):
    msg = bytes()
    while length:
        try:
            buf = os.read(fd, length)
            length -= len(buf)
            msg += buf
        except OSError,e:
          if e.errno != EINTR:
              raise
    return msg.decode('utf-8')

class JsonRPCClient:
    def __init__(self, request_observer, input_fd, output_fd):
        self._input_fd = input_fd
        self._output_fd = output_fd
        self._no = 0
        self._requests = {}
        self._observer = request_observer

    def sendRequest(self, method, params={}, nullResponse=False):
        Id = self._no
        self._no = self._no + 1
        try:
            r = self.SendMsg(method, params, Id=Id)
        except OSError:
            self._observer.onServerDown()
            raise
        log.debug('send request: %s' % r)
        if nullResponse:
            return None
        while True:
            try:
                rr = self.RecvMsg()
            except OSError:
                self._observer.onServerDown()
                raise
            if 'id' in rr and rr['id'] == Id:
                if 'error' in rr:
                    raise Exception('bad error_code %d' % rr['error'])
                return rr['result']
        return None

    def sendNotification(self, method, params={}):
        try:
            r= self.SendMsg(method, params)
        except OSError:
            self._observer.onServerDown()
            raise
        log.debug('send notifications: %s' % r)

    def handleRecv(self):
        while EstimateUnreadBytes(self._output_fd) > 0:
            try:
                self.RecvMsg()
            except OSError:
                self._observer.onServerDown()
                raise

    def SendMsg(self, method, params={}, Id=None):
        r = {}
        r['jsonrpc'] = '2.0'
        r['method'] = str(method)
        r['params'] = params
        if Id is not None:
            r['id'] = Id
            self._requests[Id] = r
        request = json.dumps(r, separators=(',',':'), sort_keys=True)
        write_utf8(self._input_fd, u'Content-Length: %d\r\n\r\n' % len(request))
        write_utf8(self._input_fd, request)
        return r

    def RecvMsg(self):
        msg_length = self.RecvMsgHeader()
        msg = read_utf8(self._output_fd, msg_length)

        rr = json.loads(msg)
        if not 'id' in rr:
            self.OnNotification(rr)
        elif not rr['id'] in self._requests:
            self.OnRequest(rr)
        else:
            self.OnResponse(self._requests[rr['id']], rr)
            self._requests.pop(rr['id'])
        return rr

    def RecvMsgHeader(self):
        read_utf8(self._output_fd, len('Content-Length: '))
        msg = u''
        msg += read_utf8(self._output_fd, 4)
        while True:
            if msg.endswith('\r\n\r\n'):
                break
            if len(msg) >= 23:  # sys.maxint + 4
                raise Exception('bad protocol')
            msg += read_utf8(self._output_fd, 1)

        msg = msg[:-4]
        length = int(msg)
        return length

    def OnNotification(self, request):
        log.debug('recv notification: %s' % request)
        self._observer.onNotification(request['method'], request['params'])

    def OnRequest(self, request):
        log.debug('recv request: %s' % request)
        self._observer.onRequest(request['method'], request['params'])

    def OnResponse(self, request, response):
        log.debug('recv response: %s' % response)
        self._observer.onResponse(request, response['result'])
