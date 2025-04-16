import re

def extract_session_id(session_str : str) :
    _match = re.search(r"/sessions/(.*?)/contexts/", session_str)
    
    if _match :
        session_id = _match.group(1)
        return session_id

    return ""


def get_str_from_food_dict(food_dict : dict) :
    return ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])