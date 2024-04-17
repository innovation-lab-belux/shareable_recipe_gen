from firebase_admin import credentials, initialize_app, firestore
import json
import time
import random
import step03_rag_exp_tf
import concurrent.futures
import threading

lock = threading.Lock()

def init_firebase():
    service_account_key_file = "scripts/firebase_credentials.json"
    cred = credentials.Certificate(service_account_key_file)
    app = initialize_app(cred, options={"databaseURL": "https://recipegen-305f4-default-rtdb.europe-west1.firebasedatabase.app/"})
    return app

def push_to_database(json_article):
    db = firestore.client()
    articles_ref = db.collection("Outputs")
    data = json.loads(json_article)
    try:
        with lock:
            result = articles_ref.add(data)
            print("Document added successfully.")
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
    except Exception as e:
        print("Error:", e)

def get_recipe_name():
    db = firestore.client()
    ref = db.collection("Inputs")
    documents = ref.stream()
    for doc in documents:
        return doc.get("recipe_name")

def get_uuid():
    db = firestore.client()
    ref = db.collection("Inputs")
    documents = ref.stream()
    for doc in documents:
        return doc.get("UUID")

def transform_json(json_file, sources):
    # print("json file: ", json_file)
    # json_file = json_file[0]
    # json_file = json_file.replace("json)", "")
    # json_file = json_file.replace("```", "")

    # print("json file modified: ", json_file)

    if isinstance(json_file, str):  
        recipe_dict = json.loads(json_file)  
    else:
        json_article = json_file[0]
        recipe_dict = json.loads(json_article)
    
    price = round(random.uniform(5, 7), 2)
    recipe_dict["price"] = f"${price}"

    recipe_dict["ingredients"] = recipe_dict["ingredients"].replace(",", "\n")

    recipe_dict["sources"] = str(sources)
    # recipe_dict["sources"] = recipe_dict["sources"].lower().replace("chunk", "recipe")

    sustainability_score = int(recipe_dict["sustainability_index"])
    score = "\u2605" * sustainability_score + "\u2606" * (5 - sustainability_score)
    recipe_dict["sustainability_index"] = score
    
    recipe_dict["nutrients"] = recipe_dict["nutrients"].replace(",","\n")
    return json.dumps(recipe_dict, indent=4)

def parse_json(json_file):
    if json_file.startswith("```json") and json_file.endswith("```"):
        json_content = json_file[len("```json") : -len("```")]
        # print("parsed json: ", json_content)
        return json_content
    else:
        return json_file


def thread_function(input_recipe, uuid):
    print("Thread   : start")
    print("recipe: ", input_recipe)
    print("uuid: ", uuid)
    try:
        json_article, sources = step03_rag_exp_tf.main(input_recipe, uuid)
        # print("sources: ", str(sources))
        print("Thread   : RAG done")
        if json_article.startswith("```json"):
            parsed_json = parse_json(json_article)
        else:
            parsed_json = json_article
        modified_json_str = transform_json(parsed_json, sources)
        push_to_database(modified_json_str)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
    except Exception as e:
        print("An error occurred during processing:", e)
    time.sleep(3)


def get_data():
    input_recipe = get_recipe_name()
    uuid = get_uuid()
    return input_recipe, uuid

if __name__ == "__main__":
    init_firebase()
    input_recipe, uuid = get_data()
    if input_recipe and uuid:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(thread_function, input_recipe, uuid) for _ in range(3)]
            concurrent.futures.wait(futures)
        print("All threads have completed.")
    else:
        print("Failed to retrieve recipe name or UUID from Firebase.")


#TO DO:
#send the LLM's response in the right format
#add a data formating validation loop to check if the document to send is in the right format, if not, make the corrections to push it
#check the possibilities for streaming, but since there is no proper multi threading system in python, it could be impossible
#continue to learn about multi threading, try to really understand the tutorial https://realpython.com/intro-to-python-threading/
#make a system for the front end to always listen and being able to push new recipes without having to refresh the page
#call rui and try to run it on my own container
#versioning when the problem with git is solved

#recuperer les sources
#prompt exfiltration