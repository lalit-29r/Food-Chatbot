from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import db_handler
import generic_helper

app = FastAPI()

inprogress_order = {}

@app.post('/')
async def root(request: Request):
    payload = await request.json()

    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']

    session_id = generic_helper.extract_session_id(output_contexts[0]['name'])

    intent_handler_dictionary = {
        'new.order' : new_order,
        'order.add-context:ongoing-order' : add_to_order,
        'order.remove-context:ongoing-order' : remove_from_order,
        'order.complete:context-ongoing-tracking' : complete_order,
        'track.order:context-ongoing-tracking' : track_order
    }

    return intent_handler_dictionary[intent](session_id, parameters)
        

def new_order(session_id : str, parameters : dict) :
    if session_id in inprogress_order :
        del inprogress_order[session_id]

def add_to_order(session_id : str, parameters : dict) :
    food_items = parameters['food-item']
    quantities = parameters['quantity']

    if len(food_items) != len(quantities) :
        fulfillment_text = "Sorry I didn't understand. Can you please clearly specify food items and quantity."
    else :
        new_food_dict = dict(zip(food_items, quantities))

        if session_id in inprogress_order :
            inprogress_order[session_id].update(new_food_dict)
        else :
            inprogress_order[session_id] = new_food_dict

        order_str = generic_helper.get_str_from_food_dict(inprogress_order[session_id])
        fulfillment_text = f"So far you have {order_str}.\nDo you need anything else?"

    return JSONResponse(content={
            "fulfillmentText": fulfillment_text
    })

def remove_from_order(session_id : str, parameters : dict) :
    if session_id in inprogress_order :
        food_items = parameters['food-item']

        removed_items = []
        items_not_in_order = []

        for item in food_items :
            if item in inprogress_order[session_id] :
                del inprogress_order[session_id][item]
                removed_items.append(item)
            else :
                items_not_in_order.append(item)

        if len(removed_items) > 0 :
            fulfillment_text = f"Removed {', '.join(removed_items)} from the order!"

        if len(items_not_in_order) > 0 :
            fulfillment_text += f" Your current order does not had {', '.join(items_not_in_order)}."
            
        if len(inprogress_order[session_id].keys()) == 0 :
            fulfillment_text += f" Your order is currently empty."
        else :
            order_str = generic_helper.get_str_from_food_dict(inprogress_order[session_id])
            fulfillment_text += f" Your current order includes {order_str}."
    else :
        fulfillment_text = "Sorry, something went wrong with your order. Could you please try placing it again?"

    return JSONResponse(content={
            "fulfillmentText": fulfillment_text
    })

def complete_order(session_id : str, parameters : dict) :
    if session_id in inprogress_order :
        order = inprogress_order[session_id]

        order_id = save_to_database(order)
        if order_id == -1 :
            fulfillment_text = "Sorry, I'm unable to place your order due to a backend error." \
                                "Please try again shortly."
        else :
            order_total = db_handler.get_total_order_price(order_id)
            fulfillment_text = "Awesome! Your order has been placed successfully." \
                                f"Your Order ID is #{order_id}." \
                                f"The total amount is {order_total}, payable at the time of delivery."
        
        del inprogress_order[session_id]
    else :
        fulfillment_text = "I'm sorry, but I couldn't find your order. Could you please place a new one?"

    return JSONResponse(content={
            "fulfillmentText": fulfillment_text
    })

def save_to_database(order : dict) :
    next_order_id = db_handler.get_next_order_id()
    
    for food_item, quantity in order.items() :
        rcode = db_handler.insert_order_item(next_order_id, food_item, quantity)
        if rcode == -1 :
            return -1
    
    db_handler.insert_order_tracking(next_order_id, "In progress")

    return next_order_id
    
def track_order(session_id : str, parameters : dict) :
    order_id = int(parameters['order-id'])
    status = db_handler.get_order_status(order_id)

    if status :
        fulfillment_text = f"Order status for order ID : {order_id} is {status}"
    else :
        fulfillment_text = f"No order found with order ID : {order_id}"

    return JSONResponse(content={
            "fulfillmentText": fulfillment_text
    })
