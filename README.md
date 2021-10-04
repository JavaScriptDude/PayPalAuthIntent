## PayPalAuthIntent
Example of Using PayPal AUTHORIZE Intent Using REST APIs

This tool is intended as a sample for consuming PayPal APIs and for testing.

This tool will simulate Auth Intent and REST calls end to end and includes google-chrome launching, watching and http callbacks from PayPal UI.

This example is coded to have the Order left in APPROVED status after the user clicks `Continue` button. The Authorization (completion) of order is left to the client such as after the user is presented with a final `Confirmation` screen. This is similar to how Spotify utilizes PayPal.

To run this, you will need an account in sandbox.paypal.com and enable REST API's

For Environment variables create file `~/.paypal/acmeinc_sandbox/.env` and put into it:
```
PP_CLIENT_ID="<<client_id>>"
PP_CLIENT_SECRET="<<client_secret>>"
```

#### Running:
```python3 main.py```


### Sample Outputs:

#### User Clicked `Continue`:
```
211003-231435.937 main.py:44 - Calling PayPal REST API to create Order
211003-231437.260 main.py:56 - start_link: https://www.sandbox.paypal.com/checkoutnow?token=498032340R017683K
211003-231437.541 main.py:66 - Order 498032340R017683K is created. Loading PayPal dialog using Chrome...
You may hit `Continue`, `Cancel and return ...` or close the chrome window
211003-231437.545 helpers.py:312 - Watching for browser being closed ...
211003-231448.176 main.py:130 - WebServer called: /pp_ord_accepted?token=498032340R017683K&PayerID=5LT9QAPV5QQ7W
211003-231448.176 helpers.py:89 - Server being shut down
211003-231448.177 helpers.py:332 - Closing browser
211003-231448.902 main.py:92 - User approved the order by hitting CONTINUE
211003-231448.902 main.py:94 - Calling PayPal REST API to authorize Order ...
211003-231450.242 main.py:102 - 
Order Auth Result:
  -  id: 498032340R017683K
  -  intent: AUTHORIZE
  -  status: COMPLETED
  -  create_time: 2021-10-04T03:14:36Z
  -  update_time: 2021-10-04T03:14:49Z

211003-231450.738 main.py:111 - Order Approved and completed
211003-231450.738 main.py:114 - DONE
```

#### User Clicked `Cancel and return ...`:
```
211003-231725.986 main.py:44 - Calling PayPal REST API to create Order
211003-231727.046 main.py:56 - start_link: https://www.sandbox.paypal.com/checkoutnow?token=4NV01103CF1182546
211003-231727.387 main.py:66 - Order 4NV01103CF1182546 is created. Loading PayPal dialog using Chrome...
You may hit `Continue`, `Cancel and return ...` or close the chrome window
211003-231727.390 helpers.py:312 - Watching for browser being closed ...
211003-231736.286 main.py:130 - WebServer called: /pp_ord_cancelled?token=4NV01103CF1182546
211003-231736.287 helpers.py:89 - Server being shut down
211003-231736.288 helpers.py:332 - Closing browser
211003-231736.805 main.py:76 - PayPal user cancelled or closed window
211003-231736.806 main.py:78 - Calling PayPal REST API to cancel Order ...
211003-231737.663 main.py:86 - Order Cancelled
211003-231737.664 main.py:114 - DONE
```

#### User closed window:
```
211003-231803.624 main.py:44 - Calling PayPal REST API to create Order
211003-231804.732 main.py:56 - start_link: https://www.sandbox.paypal.com/checkoutnow?token=77D57926RY568931E
211003-231805.125 main.py:66 - Order 77D57926RY568931E is created. Loading PayPal dialog using Chrome...
You may hit `Continue`, `Cancel and return ...` or close the chrome window
211003-231805.129 helpers.py:312 - Watching for browser being closed ...
211003-231813.146 helpers.py:324 - Browser was closed by user
211003-231813.146 helpers.py:89 - Server being shut down
211003-231813.435 main.py:76 - PayPal user cancelled or closed window
211003-231813.435 main.py:78 - Calling PayPal REST API to cancel Order ...
211003-231814.349 main.py:86 - Order Cancelled
211003-231814.350 main.py:114 - DONE
```
Note: This usecase would be handled differently in Production as we don't have access to the browser process

