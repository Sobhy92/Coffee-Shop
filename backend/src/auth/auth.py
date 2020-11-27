import json
from flask import request, _request_ctx_stack
from functools import wraps
from jose import jwt
from urllib.request import urlopen

# set domain and audience
AUTH0_DOMAIN = 'dev-vibe.us.auth0.com'
ALGORITHMS = ['RS256']
API_AUDIENCE = 'coffee'

# AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


# Auth Header

'''
@DONE implement get_token_auth_header() method
    it should attempt to get the header from the request
        it should raise an AuthError if no header is present
    it should attempt to split bearer and the token
        it should raise an AuthError if the header is malformed
    return the token part of the header
'''


def get_token_auth_header():
    data = request.headers

    # check if 'Authorization' is included in headers
    if 'Authorization' not in data.keys():
        raise AuthError(error={
            'code': 'authorization_header_missing',
            'description': 'Authorization header is expected'
        }, status_code=401)

    auth_parts = data['Authorization'].split(' ')

    # check integrity of Authorization header
    if len(auth_parts) != 2 or auth_parts[0].lower() != 'bearer':
        raise AuthError(error={
            'code': 'invalid_header',
            'description': "header must start with 'Bearer' and include proper"
                           " token"
        }, status_code=401)

    token = auth_parts[1]
    return token


'''
@DONE implement check_permissions(permission, payload) method
    @INPUTS
        permission: string permission (i.e. 'post:drink')
        payload: decoded jwt payload

    it should raise an AuthError if permissions are not included in the payload
        !!NOTE check your RBAC settings in Auth0
    it should raise an AuthError if the requested permission string is not in
    the payload permissions array return true otherwise
'''


def check_permissions(permission, payload):

    # check if 'permissions' is included in payload
    if 'permissions' not in payload.keys():
        raise AuthError(error={
            'code': 'missing_permissions',
            'description': 'permissions must be sent with token'
        }, status_code=401)

    # check if needed permission is found in our token of certain user
    if permission not in payload['permissions']:
        raise AuthError(error={
            'code': 'not_authorized',
            'description': 'needed permission not found in permissions'
        }, status_code=401)

    return True


'''
@DONE implement verify_decode_jwt(token) method
    @INPUTS
        token: a json web token (string)

    it should be an Auth0 token with key id (kid)
    it should verify the token using Auth0 /.well-known/jwks.json
    it should decode the payload from the token
    it should validate the claims
    return the decoded payload

    !!NOTE urlopen has a common certificate error described here:
    https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
'''


def verify_decode_jwt(token):

    # read data from auth0
    jsonurl = urlopen("https://" + AUTH0_DOMAIN + "/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read().decode('utf-8'))
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}

    # check some integrity of provided token
    if 'kid' not in unverified_header.keys():
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization malformed.'
        }, 401)

    # get rsa key to use it in decoding
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }

    # decode the token to return the payload
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer="https://" + AUTH0_DOMAIN + "/"
            )
            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                             "description": "token is expired"}, 401)
        except jwt.JWTClaimsError:
            raise AuthError({"code": "invalid_claims",
                             "description":
                                 "incorrect claims,"
                                 "please check the audience and issuer"}, 401)
        except Exception:
            raise AuthError({"code": "invalid_header",
                             "description":
                                 "Unable to parse authentication"
                                 " token."}, 401)

    raise AuthError({"code": "invalid_header",
                     "description": "Unable to find appropriate key"}, 401)

'''
@DONE implement @requires_auth(permission) decorator method
    @INPUTS
        permission: string permission (i.e. 'post:drink')

    it should use the get_token_auth_header method to get the token
    it should use the verify_decode_jwt method to decode the jwt
    it should use the check_permissions method validate claims and check the
    requested permission return the decorator which passes the decoded payload
    to the decorated method
'''


def requires_auth(permission=''):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(*args, **kwargs)
        return wrapper

    return requires_auth_decorator
