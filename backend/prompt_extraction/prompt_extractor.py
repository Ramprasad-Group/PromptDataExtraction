import re
import time
import json
import random
import openai
import pylogg

try:
    import polyai.api as polyai
    polyai_ok = True
except:
    polyai_ok = False

from backend.text.normalize import TextNormalizer
from backend.prompt_extraction.shot_selection import ShotSelector
from backend.postgres.orm import APIRequests, PaperTexts, ExtractionMethods
from backend.prompt_extraction.exllama_model import ExLlamaV2Model

log = pylogg.New('llm')

model_name = 'llama3'
max_seq_len = 4000
max_new_tokens = 512
model_directory= "/data/sonakshi/SynthesisRecipes/models/Llama-3-8B-Instruct-exl2"
model = ExLlamaV2Model(model_directory, max_new_tokens= max_new_tokens, max_seq_len = max_seq_len, model_name=model_name)


class LLMExtractor:
    PROMPTS = [
        "Extract all numbers in JSONL format with 'material', 'property', 'value', 'condition' columns.",
        "Extract all {property} values in JSONL format with 'material', 'property', 'value', 'condition' columns.",
    ]

    def __init__(self, db, method : ExtractionMethods) -> None:
        self.db = db    # postgres db session handle.
        self.method = method
        self.shot_selector : ShotSelector = None
        self.normalizer = TextNormalizer()

        self.model = self.method.model
        self.api = self.method.api

        # All other API settings should be in the info dictionary of the
        # extraction method. This helps us have a single source of truth.
        self.user = self._get_param('user', True)
        self.max_api_retries = self._get_param('max_api_retries', False, 1)
        self.api_retry_delay = self._get_param('api_retry_delay', False, 2)
        self.api_request_delay = self._get_param('api_request_delay', False, 0)
        self.temperature = self._get_param('temperature', False, 0.001)
        self.shots = self._get_param('n_shots', False, 0)
        self.delay_multiplier = self._get_param('delay_multiplier', False, 2)

        property = self._get_param('property', False, None)
        prompt_id = self._get_param('prompt_id', False, 0)
        
        # Format the prompt with the specified property string if any.
        self.prompt = self._get_param('prompt', False,
                            self.PROMPTS[prompt_id].format(property=property))

        log.note("Using Prompt: {}", self.prompt)

        # Save the changes made to method extraction info.
        self.db.commit()
        log.trace("Initialized {}", self.__class__.__name__)


    def process_paragraph(self, para : PaperTexts) -> tuple[list[dict], int]:
        """ Run the steps to send request to LLM, get response and parse the
            output.

            para:   The reference paragraph which will be processed.

            Returns (
                [{material: '', property: '', value: ''}],
                ID of the API request.
            )

        """
        text = self._preprocess_text(para.text)
        prompt = self._add_prompt(text)
        messages = self._get_example_messages(text)
        response, apireqid = self._ask_llm(para, prompt, messages)

        if response is None:
            return [], None

        data = self._extract_data(response)
        return data, apireqid
    
    def _get_param(self, name : str, required : bool, default = None):
        """ Returns the value of a parameter or it's default.
            The default value is written to method's info section.
            Raises exception if the parameter is required and not provided.
        """
        info = dict(self.method.extraction_info)
        if required:
            if name not in info:
                raise ValueError(f"'{name}' not set in extraction_info")
        else:
            if name not in info:
                info[name] = default
                # Assignment required for sqlalchemy dict updates.
                self.method.extraction_info = info
        return info.get(name, default)

    def _preprocess_text(self, text : str) -> str:
        text = self.normalizer.normalize(text)
        return text
    
    def _add_prompt(self, text : str) -> str:
        return f"{text}\n\n{self.prompt}"

    def _get_example_messages(self, text : str) -> list[dict]:
        records = []
        messages = []
        if self.shot_selector:
            records = self.shot_selector.get_best_shots(text, self.shots)

        for example in records:
            messages.append({
                "role": "user",
                "content": self._add_prompt(example['text'])
            })
            messages.append({
                "role": "assistant",
                "content": json.dumps(example['records']) + "\n"
            })

        return messages
    
    def _ask_llm(self, para : PaperTexts, prompt : str,
                 messages : list[dict]) -> tuple[dict, int]:
        """ Try to get a response from the API by making repeated requests
            until successful.
        """
        # Store request info to database.
        reqinfo = APIRequests()
        reqinfo.model = self.model 
        reqinfo.api = self.api
        reqinfo.para_id = para.id
        reqinfo.method_id = self.method.id
        reqinfo.status = 'preparing'
        reqinfo.request = prompt
        reqinfo.response = None
        reqinfo.response_obj = None

        reqinfo.details = {}
        reqinfo.details['n_shots'] = len(messages) // 2
        reqinfo.details['user'] = self.user

        messages.append({"role": "user", "content": prompt})
        reqinfo.request_obj = messages

        # Make request.
        retry_delay = self.api_retry_delay
        jitter = 0.1

        t2 = log.info("Making API request to {}.", self.api)
        output = None

        for retry in range(self.max_api_retries+1):
            if retry > 0:
                log.info("Retry: {} / {}", retry, self.max_api_retries)

            try:
                output = self._make_request(messages)
                time.sleep(self.api_request_delay)
                break
            except Exception as err:
                log.warn("API request error: {}", err)

                reqinfo.status = 'error'
                reqinfo.response_obj = dict(error=str(err))

                # Increment/decrement the retry_delay
                if retry > 0:
                    retry_delay *= 1 + \
                        self.delay_multiplier * (1 + jitter *random.random())

                # Wait
                log.info("Waiting for {:.2f} seconds ...", retry_delay)
                time.sleep(retry_delay)


        reqinfo.details['retries'] = retry

        log.trace("API Response: {}", output)

        reqinfo.details['elapsed'] = t2.elapsed()

        if output is None:
            reqinfo.status = 'failed'
            log.error("API request failed.")
        else:
            reqinfo.status = 'done'
            try:
                reqinfo.response_obj = json.loads(str(output))
                str_output = output["choices"][0]["message"]["content"]
                reqtok = output["usage"]["prompt_tokens"]
                resptok = output["usage"]["completion_tokens"]
                reqinfo.response = str_output
                reqinfo.request_tokens = reqtok
                reqinfo.response_tokens = resptok
                reqinfo.status = 'ok'
            except Exception as err:
                log.error("Failed to parse API output: {}", err)
                reqinfo.status = 'output parse error'

        # Store response info.
        reqinfo.insert(self.db)

        # Commit
        reqinfo.commit(self.db)

        t2.done("API Request #{} processed.", reqinfo.id)
        return output, reqinfo.id
    
    def _make_request(self, messages : list[dict]) -> dict:
        """ Send the request to the specified API endpoint. """
        response = None
        if self.api == 'openai':
            response = openai.ChatCompletion.create(
                model = self.model,
                temperature = self.temperature,
                messages = messages
            )
        elif self.api == 'polyai':
            if not polyai_ok:
                log.critical("PolyAI is not available.")
                return response
            else:
                response = polyai.ChatCompletion.create(
                    model = self.model,
                    temperature = self.temperature,
                    messages = messages
                )
        else:
            response = model.generate_text(messages)
            # raise NotImplementedError("Unknown API", self.api)

        return response
    
    def _extract_data(self, response : dict) -> list[dict]:
        """ Post process the LLM output and extract the embedded data. """
        data = []
        try:
            str_output = response["choices"][0]["message"]["content"]
        except:
            str_output = response #when using exllama
        log.trace("Parsing LLM output: {}", str_output)

        try:
            records = self._jsonl_safe_load(str_output)
        except:
            return data
        
        material = None
        prop = None 
        value = None

        for record in records:
            material = record.get("material", None)
            if material:
                prop = record.get("property", None)
                if prop:
                    value = record.get("value", None)
                if not value:
                    value = record.get("numeric value", None)

            condition = record.get("condition", record.get('conditions'))
            if condition == "None" or condition is None:
                condition = ""

            if material and prop and value:
                data.append(
                    {
                        'material': material, 'property': prop, 'value': value,
                        'condition': condition
                    }
                )

        return data

    def _jsonl_safe_load(self, jsonstr : str) -> list[dict]:
        records = []
        try:
            records = json.loads(jsonstr)
        except:
            # Try to fix the malformed json.
            if self.api == "polyai":
                jsonstr = jsonstr.split("###")[0].strip()

            # Multiple jsonl sections.
            jsonstr = jsonstr.replace("}][{", "}, {")
            jsonstr = jsonstr.replace("}] [{", "}, {")
            jsonstr = jsonstr.replace("}]  [{", "}, {")
            jsonstr = jsonstr.replace("}]\n[{", "}, {")

            # Missing comma
            jsonstr = jsonstr.replace('""', '", "')
            jsonstr = jsonstr.replace('" "', '", "')
            jsonstr = jsonstr.replace('"\n"', '", "')

            jsonstr = jsonstr.replace(': None, "', ': "None", "')
            jsonstr = jsonstr.replace(': None}', ': "None"}')


            if jsonstr.endswith("."):
                jsonstr = jsonstr.removesuffix(".")

            if jsonstr.endswith("}"):
                jsonstr += "]"

            if "[{" in jsonstr:
                jsonstr = jsonstr.replace('"]', '"}]')

            jsonstr = jsonstr.replace("\%", "%")
            jsonstr = jsonstr.replace("\*", "*")
            jsonstr = jsonstr.replace("\α", "α")
            jsonstr = jsonstr.replace(r"\mu", r"\\mu")
            jsonstr = jsonstr.replace(r"\beta", r"\\beta")
            jsonstr = jsonstr.replace(r"\zeta", r"\\zeta")
            jsonstr = jsonstr.replace(r"\alpha", r"\\alpha")
            jsonstr = jsonstr.replace(r"\gamma", r"\\gamma")

            # Retry parsing json.
            try:
                records = json.loads(jsonstr)
            except Exception as err:
                log.error("Failed to parse LLM output as JSON: {}", err)
                log.info("Post-processed JSON: {}", jsonstr)
                raise err

        return records
