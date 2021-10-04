### PayPalAuthIntent
Example of Using PayPal AUTHORIZE Intent Using REST APIs

This tool will simulate Auth Intent and REST calls end to end and includes google-chrome launching, watching and http callbacks from PayPal UI.


To run this, you will need an account in sandbox.paypal.com and enable REST API's

For Environment variables create file `~/.paypal/acmeinc_sandbox/.env` and put into it:
```
PP_CLIENT_ID="<<client_id>>"
PP_CLIENT_SECRET="<<client_secret>>"
```


#### Running:
```python3 main.py```
