def get_api_token():
    try:
        with open ('api_token.txt', 'r') as f:
            api_token = f.readline()
        return api_token
    except:
        assert api_token, 'Whoops! Please provide an api_token.'