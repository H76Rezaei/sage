import pandas as pd
import re
import numpy as np
import torch
import nltk
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from transformers import GPT2LMHeadModel, GPT2Tokenizer

# Download necessary NLTK data if not already downloaded
nltk.download('stopwords')
nltk.download('punkt')
nltk.download('wordnet')

# Set up English stop words and initialize the lemmatizer
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

# Load spaCy model for Named Entity Recognition (NER)
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print("Downloading spaCy model 'en_core_web_sm' ...")
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Load GPT2 model and tokenizer for perplexity calculation and token counting
device = 'cuda' if torch.cuda.is_available() else 'cpu'
gpt2_model = GPT2LMHeadModel.from_pretrained("gpt2-medium").to(device)
gpt2_tokenizer = GPT2Tokenizer.from_pretrained("gpt2-medium")

# Load CSV files containing conversation logs and generated responses
generated_responses = pd.read_csv("generated_responses.csv")
conversation_logs_sample = pd.read_csv("conversation_logs_sample.csv")

# Merge the two DataFrames on matching IDs (using 'log_id' and 'id')
merged_logs = pd.merge(generated_responses, conversation_logs_sample, left_on='log_id', right_on='id', how='left')

# Drop unnecessary columns
columns_to_drop = ['created_at', 'id_x', 'conv_id', 'turn_id', 'user_input']
merged_logs = merged_logs.drop(columns=columns_to_drop, errors='ignore')

# Filter for specific version IDs (example: versions 3, 5, 9, 11, 14)
selected_versions = [3, 5, 9, 11, 14]
filtered_logs = merged_logs[merged_logs['version_id'].isin(selected_versions)].copy()

#  Define Evaluation Functions 
def preprocess_text(text: str) -> str:

    if pd.isna(text):
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    tokens = word_tokenize(text)
    tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words]
    return " ".join(tokens)

def calculate_keyword_recall(memory_text: str, response_text: str) -> float:
  
    memory_keywords = set(preprocess_text(memory_text).split())
    response_keywords = set(preprocess_text(response_text).split())
    
    if not memory_keywords:
        return float('nan')
    
    common_keywords = memory_keywords.intersection(response_keywords)
    recall_score = len(common_keywords) / len(memory_keywords)
    return recall_score

def extract_entities(text: str) -> set:
    
    doc = nlp(text)
    return set(ent.text.lower() for ent in doc.ents)

def calculate_entity_overlap(memory_text: str, response_text: str) -> float:
    
    memory_entities = extract_entities(memory_text)
    response_entities = extract_entities(response_text)
    
    if not memory_entities or not response_entities:
        return float('nan')
    
    common_entities = memory_entities.intersection(response_entities)
    
    precision = len(common_entities) / len(response_entities) if response_entities else 0
    recall = len(common_entities) / len(memory_entities) if memory_entities else 0
    
    if precision + recall == 0:
        return 0.0
    
    f1_score = 2 * precision * recall / (precision + recall)
    return f1_score

def calculate_perplexity(text: str, model, tokenizer) -> float:
   
    encodings = tokenizer(text, return_tensors='pt', truncation=True, max_length=1024).to(model.device)
    nlls = []
    with torch.no_grad():
        # Process the text in chunks (if needed) to avoid length issues
        for i in range(0, encodings.input_ids.size(1), 1024):
            begin_loc = i
            end_loc = min(i + 1024, encodings.input_ids.size(1))
            input_ids = encodings.input_ids[:, begin_loc:end_loc]
            target_ids = input_ids.clone()
            outputs = model(input_ids, labels=target_ids)
            neg_log_likelihood = outputs.loss
            nlls.append(neg_log_likelihood)
    ppl = torch.exp(torch.stack(nlls).mean())
    return ppl.item()


keyword_recalls = []
entity_overlap_scores = []
perplexities = []
token_counts = []

for index, row in filtered_logs.iterrows():
    memory_text = row['default_bot_response']
    response_text = row['generated_response']
    
    # Calculate Keyword Recall Score
    if pd.isna(memory_text):
        keyword_recalls.append(float('nan'))
    else:
        kr = calculate_keyword_recall(memory_text, response_text)
        keyword_recalls.append(kr)
    
    # Calculate Entity Overlap Score (F1)
    if pd.isna(memory_text):
        entity_overlap_scores.append(float('nan'))
    else:
        eos = calculate_entity_overlap(memory_text, response_text)
        entity_overlap_scores.append(eos)
    
    # Calculate Perplexity (if GPU memory issues occur, assign NaN)
    try:
        ppl = calculate_perplexity(response_text, gpt2_model, gpt2_tokenizer)
        perplexities.append(ppl)
    except torch.cuda.OutOfMemoryError:
        print(f"CUDA out of memory error at index {index}. Skipping perplexity calculation.")
        perplexities.append(float('nan'))
    
    # Token count: if output_tokens_count is not provided in the DataFrame, calculate using tokenizer
    if pd.isna(row.get('output_tokens_count')):
        token_count = len(gpt2_tokenizer.tokenize(response_text))
        token_counts.append(token_count)
    else:
        token_counts.append(row['output_tokens_count'])


filtered_logs['keyword_recall'] = keyword_recalls
filtered_logs['entity_overlap'] = entity_overlap_scores
filtered_logs['perplexity'] = perplexities
filtered_logs['output_tokens_count'] = token_counts

output_path = 'conversation_logs_with_advanced_memory_metrics.csv'
filtered_logs.to_csv(output_path, index=False, float_format='%.6f')
print(f"Advanced memory evaluation metrics saved to {output_path}")


test_memory = (
    "I visited New York last summer and attended a conference at the Javits Center. "
    "It was an amazing experience with many industry leaders."
)
test_response = (
    "During our chat, I mentioned my trip to New York where I visited famous places including "
    "the Javits Center and met several professionals."
)

print("Sanity Check Metrics:")
print(f"Keyword Recall Score: {calculate_keyword_recall(test_memory, test_response):.4f}")
print(f"Entity Overlap Score (F1): {calculate_entity_overlap(test_memory, test_response):.4f}")
