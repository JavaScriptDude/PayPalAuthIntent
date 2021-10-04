"""
# main.py

# Intall dependencies
python3 -m pip install paypalhttp paypal-checkout-serversdk python-dotenv psutils

# This test of paypal uses REST API's and the AUTHORIZE Intent

# To run this, you will need an account in sandbox.paypal.com and enable REST API's

# For Environment variables create file `~/.paypal/acmeinc_sandbox/.env` and put into it:
PP_CLIENT_ID="<<client_id>>"
PP_CLIENT_SECRET="<<client_secret>>"

# Author: https://github.com/JavaScriptDude
# License: MIT
# Home: https://github.com/JavaScriptDude/PayPalAuthIntent

"""

import os, sys, threading
from dotenv import load_dotenv
from flask import request
from flask_restx import Resource
from pptools import *

def main(argv):

    # Start server to handle PayPal UI redirect for accepted / cancelled
    ws_host='127.0.0.1'
    ws_port=9991
    web_server = WebServer(ws_host, ws_port)

    # Load Enviroment Variables
    v = os.path.expanduser('~/.paypal/acmeinc_sandbox/.env')
    assert os.path.isfile(v), f"Env file not found: {v}"
    load_dotenv(dotenv_path=v)

    # Set up client
    pp_client = Client(get_sandbox_env())

    # Create Order
    amount = 6000
    pc("Calling PayPal REST API to create Order")
    ord_result = pp_client.create_order(
         'Acme Anvil Incorporated'
        ,amount
        ,f'http://{ws_host}:{ws_port}/pp_ord_accepted'
        ,f'http://{ws_host}:{ws_port}/pp_ord_cancelled')

    pp_ordid = aget('ord_result', ord_result, 'id', True, True)


    # Get Pay Pal approve link
    (start_link, _, _) = get_link_by_rel(ord_result, 'approve')
    pc(f'start_link: {start_link}')


    # Test Order Status
    (ord_exists, ord_status, ord_info) = pp_client.get_order_info(pp_ordid)
    if not ord_exists: raise Exception(f"Order does not exist: {pp_ordid}")
    if not ord_status == 'CREATED':
        raise Exception(f"Unexpected order status: {ord_status}. Expecting CREATED.")

    pc(f"Order {pp_ordid} is created. Loading PayPal dialog using Chrome...\n" 
       +"You may hit `Continue`, `Cancel and return ...` or close the chrome window")


    # launch Chrome with PayPal UI
    launch_browser_and_watch(web_server, start_link)


    # Get Order status and decide if its been cancelled
    (ord_exists, ord_status, ord_info) = pp_client.get_order_info(pp_ordid)
    if ord_status == 'CREATED':
        pc("PayPal user cancelled or closed window")

        pc('Calling PayPal REST API to cancel Order ...')
        pp_client.cancel_order(pp_ordid)

        # Check status of order
        (ord_exists, ord_status, ord_info) = pp_client.get_order_info(pp_ordid)
        if ord_exists: 
            raise Exception(f"Order exists but should be deleted: {pp_ordid}. ord_info: {ord_info}")

        pc("Order Cancelled")

    elif not ord_status == 'APPROVED':
        raise Exception(f"Unexpected order status: {ord_status}. Expecting APPROVED.")

    else:
        pc('User approved the order by hitting CONTINUE')

        pc('Calling PayPal REST API to authorize Order ...')
        resu = pp_client.authorize_order(pp_ordid)

        def _aget_strings(a):
            sb = StringBuffer()
            for k in a: sb.a(f"  -  {k}: {aget('resu', resu, k, True, True)}")
            return sb.ts('\n')

        pc(f"\nOrder Auth Result:\n{_aget_strings(['id', 'intent','status','create_time', 'update_time'])}\n")


        # Check status of order
        (ord_exists, ord_status, ord_info) = pp_client.get_order_info(pp_ordid)
        if not ord_exists: raise Exception(f"Order does not exist: {pp_ordid}")
        if not ord_status == 'COMPLETED':
            raise Exception(f"Unexpected order status: {ord_status}. Expecting COMPLETED.")

        pc("Order Approved and completed")


    pc("DONE\n.")

    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(1)
        

# flask_restx server for handling accepted / cancelled redirections from PayPal UI
class WebServer(QWebServer):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        super().__init__(host, port)

        @self.api.route('/pp_ord_accepted', '/pp_ord_cancelled', resource_class_kwargs=self._build_kwargs(pc))
        class pp_ord_route(QResource):
            def run(self):
                self.pc('WebServer called: {0}', request.full_path)
                self.shutdown_server()
                return self.html_response('Page will close...')

        self.start()

        
            

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as ex:
        pc(f"Fatal exception: {dumpCurExcept(ex)}")
