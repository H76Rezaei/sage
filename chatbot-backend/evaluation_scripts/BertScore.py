import pandas as pd
import numpy as np
import os
import logging
from bert_score import score  

# Configure logging to display information during execution
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def preprocess_text(text: str) -> str:
   
    if pd.isna(text):
        return ""
    return text.strip().lower()

def compute_bertscore(reference: str, generated: str, model_type: str = "roberta-large", lang: str = "en") -> float:
   
    # Preprocess texts
    reference = preprocess_text(reference)
    generated = preprocess_text(generated)
    
    # If either text is empty, return NaN
    if reference == "" or generated == "":
        return np.nan
    
    # Compute BERTScore; the score() function returns precision, recall and F1
    P, R, F1 = score([generated], [reference], lang=lang, model_type=model_type, verbose=False)
    return F1.item()

def evaluate_bertscore(generated_csv: str, conversation_csv: str, output_csv: str, 
                       selected_versions, model_type: str = "roberta-large", lang: str = "en"):
   
    # Load generated responses CSV
    logging.info(f"Loading generated responses from {generated_csv}")
    generated_df = pd.read_csv(generated_csv)
    
    # Load conversation logs CSV (which includes reference responses)
    logging.info(f"Loading conversation logs from {conversation_csv}")
    conversation_df = pd.read_csv(conversation_csv)
    
    # Merge the two DataFrames based on matching IDs (e.g., 'log_id' in generated_df and 'id' in conversation_df)
    logging.info("Merging dataframes on 'log_id' and 'id'")
    merged_df = pd.merge(generated_df, conversation_df, left_on='log_id', right_on='id', how='left')
    
    # Drop unnecessary columns if present
    columns_to_drop = ['created_at', 'id_x', 'conv_id', 'turn_id', 'user_input']
    merged_df = merged_df.drop(columns=columns_to_drop, errors='ignore')
    
    # Filter for specific version IDs
    logging.info(f"Filtering data for selected version IDs: {selected_versions}")
    merged_df = merged_df[merged_df['version_id'].isin(selected_versions)].copy()
    
    # Compute BERTScore F1 for each sample between the reference response and the generated response
    logging.info("Computing BERTScore for each sample...")
    merged_df['bertscore_f1'] = merged_df.apply(
        lambda row: compute_bertscore(row['default_bot_response'], row['generated_response'], model_type, lang), axis=1)
    
    # Log the average BERTScore (F1)
    avg_bertscore = merged_df['bertscore_f1'].mean()
    logging.info(f"Average BERTScore F1: {avg_bertscore:.4f}")
    
    # Save the results to the output CSV file
    merged_df.to_csv(output_csv, index=False, float_format='%.6f')
    logging.info(f"BERTScore results saved to {output_csv}")
    
    # Sanity Check: Evaluate on a sample pair of texts
    test_memory = (
        "I visited New York last summer and attended a conference at the Javits Center. "
        "It was an amazing experience with many industry leaders."
    )
    test_response = (
        "During our chat, I mentioned my trip to New York where I visited famous places including "
        "the Javits Center and met several professionals."
    )
    sanity_score = compute_bertscore(test_memory, test_response, model_type, lang)
    logging.info("Sanity Check Metrics:")
    logging.info(f"Test BERTScore F1: {sanity_score:.4f}")


generated_csv = "reihane.csv"
conversation_csv = "new_conversation_logs.csv"
output_csv = "conversation_logs_with_bertscore.csv"
selected_versions = [2, 3,4, 5, 7]  # Adjust these as needed
model_type = "roberta-large"  # You can change the model type if required
lang = "en"  # Language code (default is "en")

# Execute the evaluation
evaluate_bertscore(generated_csv, conversation_csv, output_csv, selected_versions, model_type, lang)
