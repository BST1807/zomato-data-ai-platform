import os
import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector
from google import genai
from google.genai import types
from dotenv import load_dotenv
import time



load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-3.8-flash"
NEW_REVIEWS = 50
BATCH_SIZE = 10
TOP_K = 5
CACHE_FILE = "review_embeddings.parquet"

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def read_reviews_from_snowflake():
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "ZOMATO_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "ZOMATO"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "STAGING"),
    )

    # Note: SAMPLE comes directly after the table name, BEFORE WHERE
    query = f"""
        SELECT REVIEW_ID, CITY, RATING, COMMENT
        FROM ZOMATO.STAGING.STG_REVIEWS SAMPLE ({NEW_REVIEWS} ROWS)
        WHERE COMMENT IS NOT NULL
    """
    df = conn.cursor().execute(query).fetch_pandas_all()
    conn.close()

    df.columns = [col.lower() for col in df.columns]
    return df

def embed(texts):
  """Generates embeddings using Gemini embedding models with rate-limit pacing."""
  embeddings = []

  for i in range(0, len(texts), BATCH_SIZE):
    batch = texts[i : i + BATCH_SIZE]

    # Retry loop with backoff if rate limits are hit
    for attempt in range(5):
      try:
        response = client.models.embed_content(
            model=EMBEDDING_MODEL, contents=batch
        )
        for emb in response.embeddings:
          embeddings.append(emb.values)
        break
      except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
          wait_time = 15 * (attempt + 1)
          print(f"Rate limited. Waiting {wait_time}s before retrying batch...")
          time.sleep(wait_time)
        else:
          raise e

    # Small polite pause between batches to stay comfortably under RPM
    time.sleep(1.0)

  return embeddings

@st.cache_data()
def load_reviews():
    if os.path.exists(CACHE_FILE):
        return pd.read_parquet(CACHE_FILE)

    with st.spinner("Fetching reviews from Snowflake and generating embeddings..."):
        df = read_reviews_from_snowflake()
        # Drop empty strings
        df['comment'] = df['comment'].fillna("").astype(str)
        df = df[df['comment'].str.strip() != ""]
        
        df['embedding'] = embed(df['comment'].tolist())
        df.to_parquet(CACHE_FILE)
    return df

st.title("Chat with your Zomato Reviews")
st.caption(f"Searching {NEW_REVIEWS} reviews, answering with {CHAT_MODEL}")

def cosine_similarity(vec_a, vec_b):
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)

def find_similar_reviews(question, df):
    question_vector = embed([question])[0]

    scores = [cosine_similarity(question_vector, row_vec) for row_vec in df['embedding']]
    df_result = df.copy()
    df_result['score'] = scores
    return df_result.nlargest(TOP_K, 'score')

def ask_llm(question, top_reviews):
    context = ""
    for _, row in top_reviews.iterrows():
        context += f"- ({row['city']}, {row['rating']} stars): {row['comment']}\n"

    system_prompt = (
        "You are an AI assistant analyzing Zomato customer reviews. "
        "Answer the user's question ONLY using the customer reviews provided below. "
        "Be concise and objective. If the reviews don't contain enough information to answer, state that clearly."
    )

    user_content = f"Question: {question}\n\nRelevant Reviews:\n{context}"

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )
    return response.text

# Load dataset
review_df = load_reviews()

question = st.text_input(
    "Ask a question about your reviews:",
    placeholder="e.g. What are the most common complaints about delivery?"
)

if question:
    with st.spinner("Searching relevant reviews and generating response..."):
        top_reviews = find_similar_reviews(question, review_df)
        answer = ask_llm(question, top_reviews)

    st.markdown("### Answer:")
    st.write(answer)

    with st.expander("Reviews used to build this answer"):
        st.dataframe(top_reviews[['city', 'rating', 'comment', 'score']], hide_index=True)