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
from timeout import timeout, TimeoutError


def EstimateUnreadBytes(fd):
    from array import array
    from fcntl import ioctl
    from termios import FIONREAD
    buf = array('i', [0])
    ioctl(fd, FIONREAD, buf, 1)
    return buf[0]


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
        except TimeoutError:
            self._observer.onServerDown()
            raise
        log.debug('send request: %s' % r)
        if nullResponse:
            return None
        while True:
            try:
                rr = self.RecvMsg()
            except TimeoutError:
                self._observer.onServerDown()
                raise
            if rr.has_key('id') and rr['id'] == Id:
                if rr.has_key('error'):
                    raise Exception('bad error_code %d' % rr['error'])
                return rr['result']
        return None

    def sendNotification(self, method, params={}):
        try:
            r= self.SendMsg(method, params)
        except TimeoutError:
            self._observer.onServerDown()
            raise
        log.debug('send notifications: %s' % r)

    def handleRecv(self):
        while EstimateUnreadBytes(self._output_fd) > 0:
            try:
                self.RecvMsg()
            except TimeoutError:
                self._observer.onServerDown()
                raise

    @timeout(5)
    def SendMsg(self, method, params={}, Id=None):
        r = {}
        r['jsonrpc'] = '2.0'
        r['method'] = str(method)
        r['params'] = params
        if Id is not None:
            r['id'] = Id
            self._requests[Id] = r
        request = json.dumps(r, separators=(',',':'), sort_keys=True)
        os.write(self._input_fd, 'Content-Length: %d\r\n\r\n' % len(request))
        os.write(self._input_fd, request)
        return r

    @timeout(5)
    def RecvMsg(self):
        msg_length = self.RecvMsgHeader()
        msg = ''
        while msg_length:
            buf = os.read(self._output_fd, msg_length)
            msg_length -= len(buf)
            msg += buf

        rr = json.loads(msg)
        if not rr.has_key('id'):
            self.OnNotification(rr)
        elif not self._requests.has_key(rr['id']):
            self.OnRequest(rr)
        else:
            self.OnResponse(self._requests[rr['id']], rr)
            self._requests.pop(rr['id'])
        return rr

    @timeout(5)
    def RecvMsgHeader(self):
        os.read(self._output_fd, len('Content-Length: '))
        buf = ''
        buf += os.read(self._output_fd, 4)
        while True:
            if buf.endswith('\r\n\r\n'):
                break
            if len(buf) >= 23:  # sys.maxint + 4
                raise Exception('bad protocol')
            buf += os.read(self._output_fd, 1)

        buf = buf[:-4]
        length = int(buf)
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

