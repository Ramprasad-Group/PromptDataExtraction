from exllamav2 import ExLlamaV2, ExLlamaV2Config, ExLlamaV2Cache, ExLlamaV2Tokenizer
from exllamav2.generator import ExLlamaV2StreamingGenerator, ExLlamaV2Sampler
from transformers import AutoTokenizer
import time
import pylogg as log

class ExLlamaV2Model:
    def __init__(self, model_directory, model_name, max_new_tokens=150, max_seq_len = 8000):
        self.model_directory = model_directory
        # self.template_path = template_path
        self.model_name = model_name #option between [llama3, phi3]
        self.max_new_tokens = max_new_tokens
        self.max_seq_len = max_seq_len
        self.model, self.cache, self.tokenizer, self.chat_tokenizer, self.config = self.initialize_model()
        self.generator, self.settings = self.setup_generator()

    def initialize_model(self):
        """Initializes the model, tokenizer, cache, and other settings."""
        print(f"Loading model: {self.model_directory}")
        # template = "".join([line.strip() for line in open(self.template_path)])
        chat_tokenizer = AutoTokenizer.from_pretrained(self.model_directory, use_fast = False)

        # Sanity Check
        if not chat_tokenizer.chat_template:
            raise ValueError("Chat template not specified in 'tokenizer_config.json'")
        
        # chat_tokenizer.chat_template = template

        config = ExLlamaV2Config(self.model_directory)
        model = ExLlamaV2(config)
        cache = ExLlamaV2Cache(model, max_seq_len = self.max_seq_len, lazy=True)
        model.load_autosplit(cache, progress = True)
        tokenizer = ExLlamaV2Tokenizer(config)

        tokenizer.eos_token = ''
        tokenizer.eos_token_id = 128009

        return model, cache, tokenizer, chat_tokenizer, config

    def setup_generator(self):
        """Sets up the generator with the given model, cache, and tokenizer."""
        settings = ExLlamaV2Sampler.Settings()
        settings.temperature = 0.85
        settings.top_k = 50
        settings.top_p = 0.8
        settings.token_repetition_penalty = 1.01

        generator = ExLlamaV2StreamingGenerator(self.model, self.cache, self.tokenizer)
        generator.warmup()

        generator.set_stop_conditions([self.chat_tokenizer.eos_token_id])
        
        if self.model_name == 'llama3':
            stop_conditions = [self.tokenizer.eos_token_id]
            generator.set_stop_conditions(stop_conditions)
        # elif self.model_name =='phi3':
        #     generator.set_stop_conditions([self.chat_tokenizer.eos_token_id])

        return generator, settings

    def generate_text(self, chat):
        """Generates text based on the chat history."""
        prompt = self.chat_tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        log.info(f"Prompt: {prompt}")
        # input_ids = self.tokenizer.encode(prompt, add_bos=True)

        input_ids = self.chat_tokenizer.apply_chat_template(chat, tokenize=True, add_generation_prompt=True, return_tensors="pt")

        self.generator.begin_stream_ex(input_ids, self.settings, loras = None, decode_special_tokens = True)

        # if self.model_name=='phi3':
        generated_tokens = []
        output  = ''

        while True:
            res = self.generator.stream_ex()
            chunk = res["chunk"]
            output += chunk
            eos = res["eos"]

            generated_tokens += res['chunk_token_ids'][0].tolist()
            print(chunk, end="", flush=True)

            if eos or len(generated_tokens) == self.max_new_tokens:
                print("\n")
                break

        return output

        # generated_tokens = 0
        # output = ''
        # while True:
        #     res = self.generator.stream_ex()
        #     chunk = res["chunk"]
        #     output += chunk
        #     eos = res["eos"]
        #     generated_tokens += 1
        #     if eos or generated_tokens == self.max_new_tokens:
        #         break

        # return output
