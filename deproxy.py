#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import SocketServer
import os
import requests
import threading
import socket

def handler2(method, path, headers, request_body):
  print 'in handler2'
  return (601, 'Something', {'X-Header': 'Value'}, 'this is the body')

def default_handler(method, path, headers, request_body):
  print 'in default_handler'
  # returns status_code, status_message, headers (list of key/value pairs), response_body (text or stream)
  return (200, 'OK', {}, '')

class DeproxyHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
  def __init__(self, server_address, handler_function=default_handler):
    print 'in DeproxyHTTPServer.__init__'
    self.handler_function = handler_function
    HTTPServer.__init__(self, server_address, self.instantiate)

    print 'Creating server thread'
    server_thread = threading.Thread(target=self.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print 'Thread started'

  def instantiate(self, request, client_address, server):
    print 'in instantiate'
    return DeproxyRequestHandler(request, client_address, server, self.handler_function)

  def make_request(self, url, method='GET', headers={}, request_body=''):
    print 'in make_request(%s, %s, %s, %s)' % (url, method, headers, request_body)
    sent_request = requests.request(method, url, return_response=False, headers=headers, data=request_body)
    sent_request.send()
    received_response = sent_request.response
    return sent_request, received_response

class DeproxyRequestHandler(BaseHTTPRequestHandler):

  def __init__(self, request, client_address, server, handler_function):
    print 'in DeproxyRequestHandler.__init__'
    self.handler_function = handler_function
    BaseHTTPRequestHandler.__init__(self, request, client_address, server)

  def handle_one_request(self):
    """Handle a single HTTP request.

    You normally don't need to override this method; see the class
    __doc__ string for information on how to handle specific HTTP
    commands such as GET and POST.

    """
    print 'in handle_one_request()'
    try:
      self.raw_requestline = self.rfile.readline(65537)
      if len(self.raw_requestline) > 65536:
        self.requestline = ''
        self.request_version = ''
        self.command = ''
        self.send_error(414)
        return
      if not self.raw_requestline:
        self.close_connection = 1
        return
      if not self.parse_request():
        # An error code has been sent, just exit
        return

      self.incoming_request = (self.command, self.path, self.headers, self.rfile)

      resp = (self.handler_function)(self.command, self.path, self.headers, self.rfile)

      self.outgoing_response = resp

      response_code = resp[0]
      response_message = resp[1]
      response_headers = resp[2]
      response_body = resp[3]

      self.send_response(response_code, response_message)
      for name, value in response_headers.items():
        self.send_header(name, value)
      self.end_headers()
      self.wfile.write(response_body)

      self.wfile.flush() #actually send the response if not already done.

    except socket.timeout, e:
      #a read or a write timed out.  Discard this connection
      self.log_error("Request timed out: %r", e)
      self.close_connection = 1
      return

def print_request(request, heading=None):
  if heading:
    print heading
  print '  method: %s' % request.method
  print '  url: %s' % request.url
  print '  headers:'
  for name, value in request.headers.items():
    print '    %s: %s' % (name, value)
  print '  data: %s' % request.data
  print ''

def print_response(response, heading=None):
  if heading:
    print heading
  print '  url: %s' % response.url
  print '  status code: %s' % response.status_code
  print '  message: %s' % response.raw.reason
  print '  Headers: '
  for name, value in response.headers.items():
    print '    %s: %s' % (name, value)
  print '  Body:'
  print response.text

def run():
  server = 'localhost'
  port = 8081
  server_address = (server, port)

  print 'Creating receiver'
  receiver = DeproxyHTTPServer(server_address)

  print
  print 'making request'
  sent_request, received_response = receiver.make_request('http://%s:%i/abc/123' % (server,port), 'GET')
  print
  print_request(sent_request, 'Sent Request')
  print_response(received_response, 'Received Response')

  print 'handler is %s' % receiver.handler_function
  receiver.handler_function = handler2
  print 'handler is %s' % receiver.handler_function

  print
  print 'making request'
  sent_request, received_response = receiver.make_request('http://%s:%i/abc/123' % (server,port), 'GET')
  print
  print_request(sent_request, 'Sent Request')
  print_response(received_response, 'Received Response')
  
if __name__ == '__main__':
  run()
