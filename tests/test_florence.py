from transformers import AutoProcessor
from transformers import AutoModelForCausalLM

processor = AutoProcessor.from_pretrained(
    "microsoft/Florence-2-base",
    trust_remote_code=True
)

model = AutoModelForCausalLM.from_pretrained(
    "weights/icon_caption_florence",
    trust_remote_code=True
)

print("Florence Loaded Successfully!")