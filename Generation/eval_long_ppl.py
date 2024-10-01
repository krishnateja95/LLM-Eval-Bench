import torch
from tqdm import tqdm
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
from torch.nn import CrossEntropyLoss

import sys
import os

device = "cuda"
args = parse_args()

data = load_dataset(args.dataset_name,args.task, split=args.split)

# model, tokenizer = load(args.model_name_or_path)

tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
cache_dir = '/lus/grand/projects/datascience/krishnat/model_weights/LLaMA/llama_cache/'
model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True, torch_dtype=torch.bfloat16, cache_dir=cache_dir).to(device)

nlls = []
loss_fn = CrossEntropyLoss(reduction="none")
past_key_values = None

num_eval_tokens = 0
for text in data["text"][:args.num_samples]:
    encodings = tokenizer(text, return_tensors="pt")
    seq_len = encodings.input_ids.size(1)
    print(f"seq_len: {seq_len}")
    pbar = tqdm(range(0, seq_len - 1))
    for idx in pbar:
        input_ids = encodings.input_ids[:, idx : idx + 1].to(device)
        with torch.no_grad():
            outputs = model(
                input_ids,
                past_key_values=past_key_values,
                use_cache=True,
            )
            logits = outputs.logits.view(-1, model.config.vocab_size)

            past_key_values = outputs.past_key_values
            label = encodings.input_ids[:, idx + 1 : idx + 2].to(logits.device).view(-1)
            neg_log_likelihood = loss_fn(logits, label)

            if kv_cache is not None:
                past_key_values = kv_cache(past_key_values)
        nlls.append(neg_log_likelihood)
        pbar.set_description(
            f"nll: {neg_log_likelihood.item():.2f}, ppl: {torch.exp(neg_log_likelihood).item():.2f}"
        )
        num_eval_tokens += 1
        if args.num_eval_tokens is not None and num_eval_tokens >= args.num_eval_tokens:
            break
        
    if args.num_eval_tokens is not None and num_eval_tokens >= args.num_eval_tokens:
        break
ppl = torch.exp(torch.stack(nlls).mean())

with open(args.output_dir, "w") as f:
    f.write(f"model name :{args.model_name_or_path}\n")
    f.write(f"the compression method is :",args.method)
    f.write(f"mean ppl :{ppl.item()}\n")
    f.write(f"****************************************************\n")
print(f"mean ppl {ppl}")