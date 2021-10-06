# Author: https://github.com/JavaScriptDude
# License: MIT

import os
import sys
import traceback
import logging
import signal
import psutil
import time
import threading
import re
from subprocess import Popen, DEVNULL
from datetime import datetime
from pprint import pformat as pf
from flask import Flask, request, make_response
from flask_restx import Api as FlaskRestxApi, Resource
from werkzeug.serving import make_server
from urllib.parse import urlparse



browser_pid = None

log = logging.getLogger('qpaypal')

# Disable Access Logging by werkzeug
# Access logging will be handled by WSGI layer or above
log_werkzeug = logging.getLogger('werkzeug')
log_werkzeug.setLevel(logging.ERROR)


class QResource(Resource):
    def __init__(self, *class_args, **kwargs):
        self.shutdown_server = kwargs['shutdown_server']
        self.pc = kwargs['pc']
        
        super().__init__(*class_args, **kwargs)

    #abstract method
    def run(self): pass

    def get(self): return self.run()
    def post(self): return self.run()
    
    def html_response(self, html):
        response = make_response()
        response.set_data(html)
        response.status_code = 200
        response.headers['Content-Type'] = 'text/html'
        return response

    def shutdown_server(self):
        pass


class QWebServer(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        assert isinstance(host, str) and not host.strip() == '', 'host param is required'
        assert isinstance(port, int), 'port param must be an integer'
        
        self.app = app = Flask(__name__)
        self.host = host
        self.port = port
        self.api = FlaskRestxApi(self.app)
        self.srv = make_server(self.host, self.port, self.app)
        self.is_running = True

    def _build_kwargs(self, pc):
        return {'shutdown_server': self.begin_shutdown,'pc': pc}

    def start(self):
        # Finish flask_restx setup
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Start thread
        super().start()


    def run(self):
        self.srv.serve_forever()

    def _do_shutdown(self):
        self.srv.shutdown()


    def begin_shutdown(self):
        global browser_pid
        if self.is_running:
            self.is_running = False
            pc("Server being shut down")
            t = threading.Thread(target=self._do_shutdown)
            t.start()

        close_proc_if_running('browser', browser_pid)



def aget_bool(alias:str, obj, sKey, req:bool=True, defval=False):
    return aget(alias, obj, sKey, req=req, dtype=bool)

def aget_int(alias:str, obj, sKey, req:bool=True):
    return aget(alias, obj, sKey, req=req, dtype=int)

def aget_float(alias:str, obj, sKey, req:bool=True):
    return aget(alias, obj, sKey, req=req, dtype=float)

def aget_dict(alias:str, obj, sKey, req:bool=True):
    return aget(alias, obj, sKey, req=req, dtype=dict)

def aget_list(alias:str, obj, sKey, req:bool=True):
    return aget(alias, obj, sKey, req=req, dtype=list)

def aget(alias:str, obj, sKey, req:bool=True, noBlank:bool=False, dtype=str):
    v=None
    try:
        v = obj[sKey]
    except:
        try:
            v = obj.__getattribute__(sKey)
        except:
            pass

    if v is None:
        if not req:
            if isinstance(dtype, str):
                return ""
            else:
                if isInt(dtype) and dtype > 1 and dtype < 5:
                    return -1
                else:
                    return None
        raise AssertionError(f'Missing key {sKey} from {alias}')
    else:
        # Can't use isinstance as almost everything is a subclass of object
        if dtype.__name__ == 'object':
            pass
        elif not isInst(v, dtype, subclass=True):
            raise AssertionError(f'value for key {sKey} in {alias} is not a {dtype.__name__}. Got: {getClassName(v)}')

        if dtype==str: v = v.strip()
    
    return v



def isStr(v):
    if v is None: return False
    return isinstance(v, str )


def isInt(v, parse:bool=False):
    if v is None: return False
    if isinstance(v, int): return True
    if parse:
        if not isStr(v): return False
        try:
            int(v)
            return True
        except ValueError as ex:
            return False


def getClassName(o):
    if o == None: return None
    return type(o).__name__


def agetEnvVar(k:str, noBlank:bool=False) -> str:
    if not k in os.environ:
        raise AssertionError("Environment variable {0} is not defined".format(k))
    
    v = os.environ[k].strip()

    if noBlank and v == '':
        raise AssertionError("Environment variable {0} found but must not be blank".format(k))

    return v


# Does not fail on booleans ( by default Python bool is also an int :-o )
# Checks subclasses if subclass=True
def isInst(o, of, subclass:bool=False) -> bool:
    if o is None: return False
    cls = o.__class__

    if isinstance(of, type):
        if not subclass or of.__name__ == 'bool':
            return cls == of
        else:
            return issubclass(cls, of)

    else: # o is an object instance

        aClasses = cls.__mro__
        if cls == bool:
            return bool in of
        else:
            for i in range(len(of)):
                of_c = of[i]
                if not subclass or of_c.__name__ == 'bool':
                    if cls == of_c: return True
                else:
                    if issubclass(cls, of_c): return True

    return False


def dumpCurExcept(chain:bool=True):
    ety, ev, etr = sys.exc_info()
    s = ''.join(traceback.format_exception(ety, ev, etr, chain=chain))
    iF = s.find('\n')
    return s[iF+1:] if iF > -1 else s


def pc(*args):
    global log
    i = 0; a = []
    for v in args:
        a.append( ( v if i == 0 or isinstance(v, (int, float, complex, str)) else pf(v, indent=1, width=80, depth=2) ) )
        i = i + 1
    sMsg = "{}{} - {}".format(
        getMachineDTMS()
        ,(' ' + getCaller(1).__str__(0))
        ,(a[0] if i == 1 else a[0].format(*a[1:]))
    )
    log.warning(sMsg)


def getMachineDTMS(dt:datetime=None):
    dt = datetime.now() if dt is None else dt
    return dt.strftime("%y%m%d-%H%M%S.%f")[:-3]


def getCaller(depth=1):
    return StackFrameItem(sys._getframe(depth + 1))


class StackFrameItem:
    file = path = line = func = clazz = None

    def __init__(self, frame):
        sFile, sPath = splitPath(frame.f_code.co_filename)
        self.path = sPath
        self.file = sFile
        self.line = frame.f_lineno
        self.func = frame.f_code.co_name
        try:
            if 'self' in frame.f_locals:
                self.clazz = frame.f_locals['self'].__class__.__name__
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            sTB = '\n'.join(traceback.format_tb(exc_traceback))
            print("Fatal exception: {}\n - msg: {}\n stack: {}".format(exc_type, exc_value, sTB))
            None

    def __str__(self, iLevel=0):
        sRet = "{}:{}".format(self.file, self.line)
        return sRet


# usage: file,path = Q_.splitPath(s)
def splitPath(s):
    assert isinstance(s, str), "String not passed. Got: {}".format(type(s))
    s = s.strip()
    assert not s == '', "Empty string passed"
    f = os.path.basename(s)
    if len(f) == 0: return ('', s[:-1] if s[-1:] == '/' else s)
    p = s[:-(len(f))-1]
    return f, p


def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                   timeout=None, on_terminate=None):
    """Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callback function which is
    called as soon as a child terminates.
    """
    assert pid != os.getpid(), "won't kill myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        try:
            p.send_signal(sig)
        except psutil.NoSuchProcess:
            pass
    gone, alive = psutil.wait_procs(children, timeout=timeout,
                                    callback=on_terminate)
    return (gone, alive)



class StringBuffer:
    def __init__(self, s:str=None):
        self._a=[] if s is None else [s]
    def a(self, s):
        self._a.append(str(s))
        return self
    def al(self, s):
        self._a.append(str(s) + '\n')
        return self
    def ts(self, delim=''):
        return delim.join(self._a)


def launch_browser_and_watch(web_server, start_link):
    global browser_pid
    # Launch window to approve
    # To finish, close the window after hitting 'CONTINUE' button
    # Close when done or click 'Cancel and return ...'
    browser_proc = Popen(f'google-chrome {start_link}', shell=True, stdin=None, stdout=DEVNULL, stderr=DEVNULL, close_fds=True)
    browser_pid = browser_proc.pid
    
    pc('Watching for browser being closed ...')
    while web_server.is_running:
        try:
            _p = psutil.Process(browser_pid)
            _p_status = _p.status()
            if _p_status == psutil.STATUS_ZOMBIE: 
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(0.5)

    if web_server.is_running:
        pc("Browser was closed by user")
        web_server.begin_shutdown()



def close_proc_if_running(alias, pid):
    _p = psutil.Process(pid)
    if _p.is_running() and not _p.status() == psutil.STATUS_ZOMBIE:
        pc(f"Closing {alias}")
        kill_proc_tree(pid)

RE_VALID_EMAIL = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
def valid_email(email) -> bool:
    if re.fullmatch(RE_VALID_EMAIL, email):
        return True
    return False

# Validate URL
def valid_uri(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def assertValidUrl(alias, url):
    if not valid_uri(url):
        raise AssertionError(f"{alias} is invalid. Please pass valid URL. Got '{url}'")