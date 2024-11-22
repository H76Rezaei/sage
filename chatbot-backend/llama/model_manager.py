from transformers import LlamaForCausalLM, PreTrainedTokenizerFast

# Initialize Llama tokenizer and model
def get_model_and_tokenizer():
    model = LlamaForCausalLM.from_pretrained("meta-llama/Llama-3.2-1B-Instruct").to("cpu")
    tokenizer = PreTrainedTokenizerFast.from_pretrained("meta-llama/Llama-3.2-1B-Instruct")

    # Set up the pad token
    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.pad_token_id

    return model, tokenizer
