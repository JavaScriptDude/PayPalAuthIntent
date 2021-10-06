# pptools.py
# PayPal REST API Tools using v2 where possible 
# Author: https://github.com/JavaScriptDude
# License: MIT

import requests
import logging
from requests.auth import HTTPBasicAuth
from paypalhttp import HttpError
from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment
from paypalhttp.http_response import Result, HttpResponse
from paypalcheckoutsdk.orders import OrdersCreateRequest, OrdersAuthorizeRequest, OrdersGetRequest
from helpers import *

log = logging.getLogger('pptools')

def get_sandbox_env():
    return SandboxEnvironment(client_id=agetEnvVar('PP_CLIENT_ID'), client_secret=agetEnvVar('PP_CLIENT_SECRET'))

class Client(PayPalHttpClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def get_access_token(self):
        res = requests.post(
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            headers={
                'Accept': 'application/json',
                'Accept-Language': 'en_US',
            },
            auth=HTTPBasicAuth(self.environment.client_id, self.environment.client_secret),
            data={'grant_type': 'client_credentials'},
        ).json()
        return res['access_token']


    def create_order(self, purchase_units, application_context):
        
        # OPTIONAL - Validations (Fail Fast)
        assert isinstance(purchase_units, dict)\
            ,f"purchase_units is not a dict. Got {getClassName(purchase_units)}"

        assert isinstance(application_context, dict)\
            ,f"application_context is not a dict. Got {getClassName(application_context)}"        

        amount = aget_dict('purchase_units', purchase_units, 'amount', True)
        currency_code = aget('amount', amount, 'currency_code', True, True)
        value = aget('amount', amount, 'value', True, True)

        # . payee
        payee = aget_dict('purchase_units', purchase_units, 'payee', False)

        # . brand_name
        brand_name = aget('application_context', application_context, 'brand_name', False, True)
        if payee is None:
            if brand_name == '':
                pc("WARNING - Merchant block at top of UI will show Test Store because payee and brand_name are not specified")
        else:
            payee_email = aget('payee', payee, 'email_address', True, True)
            assert valid_email(payee_email), f"Email address for payee is invalid. Got '{payee_email}'"

        # . application_context - other
        aget('application_context', application_context, 'shipping_preference', True, True)
        aget('application_context', application_context, 'user_action', True, True)
        return_url = aget('application_context', application_context, 'return_url', True, True)
        cancel_url = aget('application_context', application_context, 'cancel_url', True, True)

        assertValidUrl('return_url', return_url)
        assertValidUrl('cancel_url', cancel_url)

        # End Validations
        
        
    
        request = OrdersCreateRequest()
        request.prefer('return=representation')

        request.request_body (
            {
                 "intent": "AUTHORIZE"
                ,"purchase_units": [purchase_units]
                ,'application_context': application_context
            }
        )

        ord_resp = self.execute(request)

        return get_order_result_dict(ord_resp)



    # (ord_exists, ord_status, ord_info) = get_order_info(<ordid>)
    def get_order_info(self, ordid) -> Result:
        global pp_client

        req = OrdersGetRequest(ordid)
        try:
            resp = self.execute(req)

        except HttpError as he:
            msg = he.message
            if msg.find('RESOURCE_NOT_FOUND') > -1:
                return (False, None, None)

            raise Exception(f"HTTP Error occured. Message: '{msg}', error: {he}")
    
        ord_info = get_order_result_dict(resp)
        ord_status = aget('ord_info', ord_info, 'status', True, True)
        return (True, ord_status, ord_info)


    def authorize_order(self, pp_ordid) -> dict:
        req = OrdersAuthorizeRequest(pp_ordid)
        req.prefer("return=representation")
        req.request_body({})
        
        resp = self.execute(req)

        if not resp.status_code == 201:
            raise Exception(f"Unexpected response from OrdersAuthorizeRequest: {resp.status_code}. Full response: {resp}")

        return get_order_result_dict(resp)

    # Have to use v1 API as order deletion is not available in v2 API
    def cancel_order(self, order_id) -> bool:
        uri = f'https://api-m.sandbox.paypal.com/v1/checkout/orders/{order_id}'
        res = requests.delete(
            uri,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.get_access_token()}'
            }
        )

        if not res.ok:
            raise Exception(f"\n\nPayPal API Call failed for url {uri}: {res.reason} ({res.text}).\nFull Response:\n{res}\n\n")

        return


def get_order_result_dict(ord_resp) -> dict:
    assert isinstance(ord_resp, HttpResponse), f"ord_resp is not a HttpResponse. Got: {getClassName(ord_resp)}"
    result = aget('ord_resp', ord_resp, 'result', True, True, dtype=Result)
    dResult = result.dict()
    assert isinstance(dResult, dict), f"result is not a dict. Got: {getClassName(dResult)}"
    return dResult


# (_href, _rel, _method) = get_link_by_rel(result, rel)
def get_link_by_rel(result, rel):
    assert isinstance(result, (Result, dict)), f"result is not a paypalhttp.http_response.Result. Got: {getClassName(result)}"
    links = aget('result', result, 'links', True, True, dtype=list)
    for link in links:
        if link['rel'] == rel:
            return (link['href'], link['rel'], link['method'])
    raise Exception(f"Link not found for rel '{rel}'")


