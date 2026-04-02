import pandas as pd
from flask import Flask, render_template, request
import json
import os

# --- Project Setup ---
app = Flask(__name__)

# Determine the absolute path for the CSV file for robustness
CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data.csv')

# Load the data.csv file into a Pandas DataFrame
try:
    data_df = pd.read_csv(CSV_FILE_PATH)
    # Convert key columns to lowercase for case-insensitive matching
    data_df['Item_Lower'] = data_df['Item'].str.lower()
    data_df['Category_Lower'] = data_df['Category'].str.lower()
    print("CSV loaded successfully.")
except FileNotFoundError:
    data_df = pd.DataFrame()
    print(f"ERROR: CSV file not found at {CSV_FILE_PATH}")

# --- Chatbot NLP Logic Function ---
def get_chatbot_response(query_text):
    """Interprets the user's question and returns a targeted answer based on rules."""
    if data_df.empty:
        return "ERROR: Data is not available or could not be loaded."
    
    # 1. Standardize query for processing
    query_text = query_text.strip().lower()
    words = set(query_text.split())

    if not query_text:
        return "Please ask a question about our inventory, like 'What is the price of a laptop?'"

    # 2. Find the target item or category
    
    # Simple search function to find the primary target (Item or Category)
    target_row = None
    target_items = []

    # Check for Item/Category match in the query text
    for index, row in data_df.iterrows():
        # Check if the query contains the item name
        if row['Item_Lower'] in query_text:
            target_row = row
            # If an item is found, the target category is the one it belongs to
            target_items = data_df[data_df['Category_Lower'] == row['Category_Lower']]
            break
        # Check if the query contains the category name (only if an item wasn't matched first)
        elif row['Category_Lower'] in query_text:
            target_items = data_df[data_df['Category_Lower'] == row['Category_Lower']]
            # Since we matched a category, we can use the first item in that category as a "target_row" for general info
            target_row = target_items.iloc[0] 
            break
            
    # 3. Formulate the response based on keywords and target
    
    # A. Question about price
    if any(word in words for word in ['price', 'cost', 'much']) and target_row is not None:
        return (f"The {target_row['Item']} (in the {target_row['Category']} category) "
                f"is currently priced at ₹{target_row['Price']}.")

    # B. Question about location
    elif any(word in words for word in ['location', 'where', 'stock', 'available']) and target_row is not None:
        return (f"The {target_row['Item']} is currently available in {target_row['Location']}.")
    
    # C. Question about listing a category
    elif any(word in words for word in ['list', 'show', 'category', 'what']) and target_items is not None and not target_items.empty:
        category = target_items.iloc[0]['Category'] # Get the category name from the first item
        items = target_items['Item'].tolist()
        items_str = ", ".join([f'{item}' for item in items])
        return f"We have several items in the {category} category: {items_str}."

    # D. Simple item/category match (Default Info)
    elif target_row is not None:
        return (f"I found the {target_row['Item']}. It's in the {target_row['Category']} category, "
                f"costs ${target_row['Price']}, and is available in {target_row['Location']}.")

    # E. No match found
    else:
        return "I'm sorry, I couldn't find any item or category matching your query. Try asking about a specific item like 'Laptop' or a category like 'Apparel'."

# --- Flask Routes ---
@app.route('/', methods=['GET', 'POST'])
def query_page():
    # Load history from the hidden form field on POST, otherwise start new.
    history_json = request.form.get('history', '[]')
    history = json.loads(history_json)
    
    query_input = ""
    
    if request.method == 'POST':
        query_input = request.form.get('query_box', '').strip()
        if query_input:
            # 1. Get the chatbot's answer
            answer = get_chatbot_response(query_input)
            
            # 2. Add user query and chatbot response to history
            history.append({'sender': 'user', 'message': query_input})
            history.append({'sender': 'bot', 'message': answer})
            
            # Re-dump the history after updating
            history_json = json.dumps(history)

    # Render the HTML template, passing the conversation history
    return render_template('index.html', history=history, history_json=history_json)

if __name__ == '__main__':
    app.run(debug=True)