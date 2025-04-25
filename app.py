from flask import Flask, render_template, request, redirect, url_for
import json
import requests
from datetime import datetime, timedelta
import os

# Create the application.
app = Flask(__name__)

# Some global variables
OS_DOMAIN, OS_USER_ID, USER_NAME = None, None, None
ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT = None, None, None
DID, WID, EID, CONFIG, ETYPE = None, None, None, None, None

# Get your API keys from a json file
with open('oauth_key.json') as f: 
    oauth_keys = json.load(f)
    OAUTH_CLIENT_ID = oauth_keys['OAUTH_CLIENT_ID']
    OAUTH_CLIENT_SECRET = oauth_keys['OAUTH_CLIENT_SECRET']

# === The main page ===
@app.route('/')
def index():

    response = requests.get(
        os.path.join(
            OS_DOMAIN, 
            "api/parts/d/{}/w/{}/e/{}/".format(
                DID, WID, EID
            )
        ), 
        headers={
            "Content-Type": "application/json", 
            "Accept": "application/json;charset=UTF-8;qs=0.09", 
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )
    
    PARTS = []
    if response.ok: 
        response = response.json() 
        for p in response:
            arr = [p["name"], p["partId"]]
            PARTS.append(arr)

    response = requests.get(
        os.path.join(
            OS_DOMAIN,
            "api/documents/d/{}/w/{}/elements".format(
                DID, WID
            )
        ), 
        headers={
            "Content-Type": "application/json", 
            "Accept": "application/json;charset=UTF-8;qs=0.09", 
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )
    
    ELEMENTS = []
    VSID = ""
    if response.ok: 
        response = response.json() 
        for e in response:
            arr = [e["name"], e["elementType"]]
            ELEMENTS.append(arr) 
            if e['elementType'] == 'VARIABLESTUDIO':
                VSID = e['id']
     
    if VSID != "":
        response = requests.get(
            os.path.join(
                OS_DOMAIN,
                "api/variables/d/{}/w/{}/e/{}/variables".format(
                    DID, WID, VSID
                )
            ), 
            headers={
                "Content-Type": "application/json", 
                "Accept": "application/json;charset=UTF-8;qs=0.09", 
                "Authorization": "Bearer " + ACCESS_TOKEN
            }
        )
        VARS = []
        if response.ok: 
            response = response.json() 
            variables = response[0]["variables"]
            for v in variables:
                arr = [v["name"], v["expression"]]
                VARS.append(arr)

    # Now let's try it without having to grab the Variable Studio EID.
    response = requests.get(
        os.path.join(
            OS_DOMAIN,
            "api/variables/d/{}/w/{}/e/{}/variables?includeValuesAndReferencedVariables=true".format(
                DID, WID, EID
            )
        ), 
        headers={
            "Content-Type": "application/json", 
            "Accept": "application/json;charset=UTF-8;qs=0.09", 
            "Authorization": "Bearer " + ACCESS_TOKEN
        }
    )
    VARS2 = []
    # if response.ok: 
    #     response = response.json() 
    #     print("response")
    #     print(response)
    #     variables = response[0]["variables"]
    #     for v in variables:
    #         arr = [v["name"], v["expression"]]
    #         VARS2.append(arr)
    #VARS = [1,2,3]
    return render_template('index.html', parts=PARTS, elements=ELEMENTS, vsid=VSID, vars=VARS, vars2=VARS2, config=CONFIG, etype=ETYPE)

# === Oauth stuff ===
@app.route("/login/")
def login(): 
    # When the app extension is first opened, this app page is called. 
    # It collects user information and redirects the user to Onshape's OAuth authorization page. 
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    global OS_DOMAIN, OS_USER_ID, DID, WID, EID, CONFIG, ETYPE

    # set the domain, user ID, DID, WID, EID, CONFIG for use later
    OS_DOMAIN = request.args.get('server')
    OS_USER_ID = request.args.get('userId')
    DID = request.args.get('did')
    WID = request.args.get('wvmid')
    EID = request.args.get('eid')
    extension_config = request.args.get('config')
    if extension_config == '{$configuration}':
        CONFIG = "Element not configured"
    else:
        CONFIG = extension_config
    ETYPE = request.args.get('etype')

    # If we don't have an access token, go get one.
    if not ACCESS_TOKEN: 
        return redirect(
            "https://oauth.onshape.com/oauth/authorize?response_type=code&client_id={}".format(
                OAUTH_CLIENT_ID.replace("=", "%3D")
            )
        )
    # If our access token has expired, go get a new one.
    elif datetime.now() >= EXPIRES_AT - timedelta(minutes=20): 
        response = requests.post(
            "https://oauth.onshape.com/oauth/token?grant_type=refresh_token&refresh_token={}&client_id={}&client_secret={}".format(
                REFRESH_TOKEN.replace('=', '%3D'), 
                OAUTH_CLIENT_ID.replace('=', '%3D'), 
                OAUTH_CLIENT_SECRET.replace('=', '%3D')
            ), 
            headers={'Content-Type': "application/x-www-form-urlencoded"}
        )
        response = response.json() 
        print(response)
        ACCESS_TOKEN = response['access_token']
        REFRESH_TOKEN = response['refresh_token']
        EXPIRES_AT = datetime.now() + timedelta(seconds=response['expires_in'])

    return redirect(url_for("index"))   

@app.route("/oauthRedirect/")
def authorize(): 
    # When the user authorizes the OAuth integration, Onshape's OAuth 
    # authorization page will redirect the user to this page, as registered as the redirect URL.
 
    auth_code = request.args.get('code')
    if not auth_code: 
        return "<p>User authentication failed!</p><p>Error: " + str(request.args.get('error')) + "</p>"
    
    # Use authorization code to get tokens 
    response = requests.post(
        "https://oauth.onshape.com/oauth/token?grant_type=authorization_code&code={}&client_id={}&client_secret={}".format(
            auth_code.replace('=', '%3D'), 
            OAUTH_CLIENT_ID.replace('=', '%3D'), 
            OAUTH_CLIENT_SECRET.replace('=', '%3D')
        ), 
        headers={'Content-Type': "application/x-www-form-urlencoded"}
    )
    response = response.json() 
    
    global ACCESS_TOKEN, REFRESH_TOKEN, EXPIRES_AT
    ACCESS_TOKEN = response['access_token']
    REFRESH_TOKEN = response['refresh_token']
    EXPIRES_AT = datetime.now() + timedelta(seconds=response['expires_in'])
    
    return redirect(url_for("index"))