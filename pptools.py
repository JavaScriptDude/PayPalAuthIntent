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


    # create_order('Acme Anvil Incorporated', 6000, 'http://127.0.0.1:9991/pp_ord_accepted', 'http://127.0.0.1:9991/pp_ord_cancelled')
    def create_order(self, company_name, amount, return_url, cancel_url):
        request = OrdersCreateRequest()
        request.prefer('return=representation')
        request.request_body (
            {
                "intent": "AUTHORIZE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": "USD",
                            "value": f"{amount}.00"
                        }
                    }
                ],
                # https://developer.paypal.com/docs/api/orders/v1/#definition-application_context
                'application_context': {
                     'shipping_preference': "NO_SHIPPING" # Removes shipping section
                    ,'user_action': "CONTINUE"            # Order Status will be APPROVED at callback
                    ,'brand_name': company_name           # Show in Merchant block at top of window
                    ,'return_url': return_url             # URL called on `CONTINUE`
                    ,'cancel_url': cancel_url             # URL called on `Cancel and return ...``
                }
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


