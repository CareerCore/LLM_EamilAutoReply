import pandas as pd
import numpy as np
import faiss
import json
import re
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from config import GEMINI_API_KEY, PRODUCTS_CSV, EMAILS_CSV

# Configure Gemini model
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# Load product and email data
products = pd.read_csv(PRODUCTS_CSV)
emails = pd.read_csv(EMAILS_CSV)

# Build FAISS index from product descriptions
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

product_texts = [
    f"{row['Product_Name']} {row['Description']} {row['Category']}"
    for _, row in products.iterrows()
]

embeddings = embed_model.encode(product_texts)
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(np.array(embeddings))


# Classify email and extract product ID
def classify_and_extract(email):
    prompt = f"""
    Classify this email into one of: product inquiry, complaint, other.
    Also extract the Product ID if mentioned (like ACC101).

    Return ONLY JSON:
    {{"category": "product inquiry", "product_id": "ACC101"}}

    Email: {email}
    """
    response = model.generate_content(prompt).text

    try:
        clean_text = re.sub(r"```json|```", "", response.strip()).strip()
        data = json.loads(clean_text)
        category = str(data.get("category", "")).lower().strip()
        product_id = data.get("product_id")

        if category in ["product inquiry", "product_inquiry"]:
            category = "product inquiry"
        elif category == "complaint":
            category = "complaint"
        else:
            category = "other"

        return category, product_id

    except Exception:
        return "other", None


# Find product by ID or semantic search
def retrieve_product(email, product_id):
    if product_id:
        result = products[products["Product_ID"].str.upper() == str(product_id).upper()]
        if not result.empty:
            return result.iloc[0]

    query_vec = embed_model.encode([email])
    _, indices = index.search(query_vec, 1)
    return products.iloc[indices[0][0]]


# Generate reply for product inquiry
def generate_inquiry_reply(email, product):
    prompt = f"""
    You are a customer support agent. Write a friendly and professional reply to this email.

    Customer Email: {email}

    Product: {product['Product_Name']} | {product['Category']}
    Description: {product['Description']}
    Price: {product['Price']} | Stock: {product['Stock']}

    Keep it warm and natural. Sign off as: Customer Support Team
    """
    return model.generate_content(prompt).text


# Generate reply for complaint
def generate_complaint_reply(email, product):
    prompt = f"""
    You are a customer support agent handling a complaint. Write an empathetic and helpful reply.

    Customer Complaint: {email}

    Product: {product['Product_Name']} | {product['Category']}
    Description: {product['Description']}
    Price: {product['Price']}

    Apologize sincerely and offer a refund or replacement. Sign off as: Customer Support Team
    """
    return model.generate_content(prompt).text


# Generate reply for general emails
def generate_other_reply(email):
    prompt = f"""
    You are a customer support agent. Write a polite reply to this message.

    Customer Email: {email}

    Acknowledge their message and ask for more details if needed. Sign off as: Customer Support Team
    """
    return model.generate_content(prompt).text


# Route email to the right reply function
def process_email(email):
    category, product_id = classify_and_extract(email)

    if category == "product inquiry":
        product = retrieve_product(email, product_id)
        reply = generate_inquiry_reply(email, product)
    elif category == "complaint":
        product = retrieve_product(email, product_id)
        reply = generate_complaint_reply(email, product)
    else:
        reply = generate_other_reply(email)

    return category, reply


# Run pipeline on sample emails
if __name__ == "__main__":
    sample_emails = emails.head(5)

    for i, (_, row) in enumerate(sample_emails.iterrows(), 1):
        email = row["Email_Text"]
        category, response = process_email(email)

        print("\n" + "-" * 60)
        print(f"Email #{i} | Category: {category.upper()}")
        print(f"\nCustomer Email:\n{email}")
        print(f"\nReply:\n{response}")
        print("-" * 60)