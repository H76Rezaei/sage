import pandas as pd
from sentence_transformers import SentenceTransformer, util
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
import re
import numpy as np
import nltk
from nltk.stem import WordNetLemmatizer  

# Download necessary NLTK data 
nltk.download('wordnet')
nltk.download('omw-1.4')

# Load conversation logs
#generated_responses = pd.read_csv("generated_responses.csv")
#conversation_logs_sample = pd.read_csv("conversation_logs_sample.csv")

generated_responses = pd.read_csv("new_evaluation.csv")
conversation_logs_sample = pd.read_csv("new_conversation_logs.csv")

# Merge the two DataFrames based on matching IDs
#merged_logs = pd.merge(generated_responses, conversation_logs_sample, left_on='log_id', right_on='id', how='left')

# Drop unnecessary columns
#columns_to_drop = ['created_at', 'id_x', 'conv_id', 'turn_id', 'user_input']
#merged_logs = merged_logs.drop(columns=columns_to_drop, errors='ignore') 

# Filter for specific version IDs
#selected_versions = [3, 5, 9, 11, 14]
#filtered_logs = merged_logs[merged_logs['version_id'].isin(selected_versions)].copy()

#merged_logs = pd.merge(generated_responses, conversation_logs_sample, left_on='log_id', right_on='id', how='left')

# Filter for versions 1 through 5 (adjust this list as needed)
#selected_versions = [1, 2, 3, 4, 5]
#filtered_logs = merged_logs[merged_logs['version_id'].isin(selected_versions)].copy()


# Load data
generated_responses = pd.read_csv("new_evaluation.csv")
conversation_logs_sample = pd.read_csv("new_conversation_logs.csv")

# Ensure column names are correct
print("Generated Responses Columns:", generated_responses.columns)
print("Conversation Logs Columns:", conversation_logs_sample.columns)

# Merge DataFrames on log_id
merged_logs = pd.merge(
    generated_responses, 
    conversation_logs_sample[['id', 'default_bot_response']],  # Keep only necessary columns
    left_on='log_id', 
    right_on='id',  
    how='left'
)

# Verify merge results
print(merged_logs[['log_id', 'version_id', 'default_bot_response', 'generated_response']].head(10))

selected_versions = [1, 2, 3, 4, 5]
filtered_logs = merged_logs[merged_logs['version_id'].isin(selected_versions)].copy()


# Initialize models
similarity_model = SentenceTransformer('stsb-roberta-large')
#similarity_model = SentenceTransformer('intfloat/multilingual-e5-large')


gpt2_model = GPT2LMHeadModel.from_pretrained("gpt2-medium").to('cuda' if torch.cuda.is_available() else 'cpu')
gpt2_tokenizer = GPT2Tokenizer.from_pretrained("gpt2-medium")

# Initialize lemmatizer
lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    if pd.isna(text):
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    words = text.split()
    words = [lemmatizer.lemmatize(word) for word in words] # Lemmatization
    return " ".join(words)


def calculate_semantic_similarity(default_bot_response_text, response_text):
    default_bot_response_text = preprocess_text(default_bot_response_text)
    response_text = preprocess_text(response_text)
    
    if not default_bot_response_text or not response_text:
        return np.nan
    
    default_bot_response_embedding = similarity_model.encode(default_bot_response_text, convert_to_tensor=True)
    response_embedding = similarity_model.encode(response_text, convert_to_tensor=True)

    # Print embeddings for debugging
    #print(f"default_bot_response_embedding: {default_bot_response_embedding}")
    #print(f"response_embedding: {response_embedding}")


    similarity_score = util.cos_sim(default_bot_response_embedding, response_embedding)
    return similarity_score.item()

def calculate_perplexity(text, gpt2_model, gpt2_tokenizer):
    encodings = gpt2_tokenizer(text, return_tensors='pt', truncation=True, max_length=1024).to(gpt2_model.device)
    nlls = []
    with torch.no_grad():
        for i in range(0, encodings.input_ids.size(1), 1024):
            begin_loc = i
            end_loc = min(i + 1024, encodings.input_ids.size(1))
            trg_len = end_loc - begin_loc
            input_ids = encodings.input_ids[:, begin_loc:end_loc].to(gpt2_model.device)
            target_ids = input_ids.clone()
            outputs = gpt2_model(input_ids, labels=target_ids)
            neg_log_likelihood = outputs.loss
            nlls.append(neg_log_likelihood)

    ppl = torch.exp(torch.stack(nlls).mean())
    return ppl.item()

# Adding new metrics
semantic_similarities = []
perplexities = []
token_counts = []


# Calculate metrics for each row
for _, row in filtered_logs.iterrows():
    default_bot_response_text = row['default_bot_response']  
    response_text = row['generated_response']

    # Handle cases where default_bot_response might be missing (NaN)
    if pd.isna(default_bot_response_text):
        print(f"Missing default_bot_response for log_id: {row['log_id']}. Skipping similarity calculation.")
        semantic_similarities.append(float('nan')) # Append NaN if input is missing
    else:
        semantic_similarity = calculate_semantic_similarity(default_bot_response_text, response_text)
        semantic_similarities.append(semantic_similarity)

    # Compute perplexity
    try:
        perplexity = calculate_perplexity(response_text, gpt2_model, gpt2_tokenizer)
        perplexities.append(perplexity)
    except torch.cuda.OutOfMemoryError:
        print("CUDA out of memory error. Skipping perplexity calculation for this row.")
        perplexities.append(float('nan'))

    # Compute token count 
    if pd.isna(row['output_tokens_count']):
        token_count = len(gpt2_tokenizer.tokenize(response_text))
        token_counts.append(token_count)
    else:
        token_counts.append(row['output_tokens_count'])


# Sanity Check:
test_sentences = [
    ("Hello, how are you?", "Hi, how are you?"),
    ("This is a test.", "This is not a test."),
    ("The weather is nice today.", "It is raining cats and dogs."),
    ("It's a beautiful day!", "It is a beautiful day.") # added test case
]

print("Sanity Check:")
for sent1, sent2 in test_sentences:
    similarity = calculate_semantic_similarity(sent1, sent2)
    print(f"Similarity between '{sent1}' and '{sent2}': {similarity}")


# Update the DataFrame
filtered_logs['semantic_similarity'] = semantic_similarities
filtered_logs['perplexity'] = perplexities
filtered_logs['output_tokens_count'] = token_counts
filtered_logs['avg_semantic_similarity'] = filtered_logs.groupby('version_id')['semantic_similarity'].transform('mean')


# Save the updated DataFrame with explicit float formatting
output_path = 'conversation_logs_with_metrics.csv'
filtered_logs.to_csv(output_path, index=False, float_format='%.6f') # Format to 6 decimal places

print(f"Metrics saved to {output_path}")