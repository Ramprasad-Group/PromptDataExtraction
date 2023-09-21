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

from backend.postgres.orm import APIRequests, PaperTexts
from backend.text.normalize import TextNormalizer
from backend.prompt_extraction.shot_selection import ShotSelector

log = pylogg.New('llm')

class LLMExtraction:
    def __init__(self, db, extraction_info : dict,
                 debug : bool = False) -> None:

        self.db = db    # postgres db session handle.
        self.debug = debug
        self.shot_selector : ShotSelector = None
        self.normalizer = TextNormalizer()

        self.max_api_retries = 1
        self.api_retry_delay = 2 # seconds

        self.extraction_info = extraction_info
        self.prompt_id = self._get_param('prompt_id', False, 0)
        self.api = self._get_param('api', True)
        self.user = self._get_param('user', True)
        self.model = self._get_param('model', True)
        self.temperature = self._get_param('temperature', False, 0.001)
        self.shots = self._get_param('shots', False, 0)

    def process_paragraph(self, para : PaperTexts) -> list[dict]:
        """ Run the steps to send request to LLM, get response and parse the
            output.

            para:   The reference paragraph which will be processed.

            Returns [{material: '', property: '', value: ''}]
        """
        text = self._preprocess_text(para.text)
        prompt = self._add_prompt(text)
        messages = self._get_example_messages(text)
        response = self._ask_llm(para, prompt, messages)

        if response is None:
            return None

        data = self._extract_data(response)
        return data
    
    def _get_param(self, name : str, required : bool, default = None):
        """ Returns the value of a parameter or it's default.
            Raises exception if the parameter is required and not provided.
        """
        if required:
            if name not in self.extraction_info:
                raise ValueError(f"'{name}' not set in extraction_info")
            return self.extraction_info[name]
        else:
            return self.extraction_info.get(name, default)

    def _preprocess_text(self, text : str) -> str:
        text = self.normalizer.normalize(text)
        return text
    
    def _add_prompt(self, text : str) -> str:
        prompt_list = [
            "Extract all numbers in JSONL format with 'material', 'property', 'value', 'conditions' columns."
        ]
        prompt = prompt_list[self.prompt_id]
        return f"{text}\n\n{prompt}"

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
                 messages : dict) -> dict:
        """ Try to get a response from the API by making repeated requests. """
        # Store request info to database.
        reqinfo = APIRequests()
        reqinfo.model = self.model 
        reqinfo.api = self.api
        reqinfo.para_id = para.id
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
        delay = self.api_retry_delay
        exponential_base = 2
        jitter = 0.1

        t2 = log.info("Making API request to {}.", self.api)
        output = None

        for retry in range(self.max_api_retries):
            if retry > 0:
                log.info("Retry: {} / {}", retry, self.max_api_retries)

            try:
                output = self._make_request(messages)
                break
            except Exception as err:
                log.warn("API request error: {}", err)

                if self.debug:
                    raise err

                reqinfo.status = 'error'

                # Increment the delay
                delay *= exponential_base * (1 + jitter * random.random())
                # Wait
                log.info("Waiting for {:.2f} seconds ...", delay)
                time.sleep(delay)

        reqinfo.details['retries'] = retry

        t2.done("Request processed.")
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
        reqinfo.commit(self.db)
        return output
    
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
            raise NotImplementedError("Unknown API", self.api)

        return response
    
    def _extract_data(self, response : dict) -> list[dict]:
        """ Post process the LLM output and extract the embedded data. """
        data = []
        str_output = response["choices"][0]["message"]["content"]
        log.trace("Parsing LLM output: {}", str_output)

        try:
            records = json.loads(str_output)
        except:
            log.error("Failed to parse LLM output as JSON.")
            return data

        for record in records:
            material = record.get("material", None)
            if material:
                prop = record.get("property", None)
                if prop:
                    value = record.get("value", None)
                if not value:
                    value = record.get("numeric value", None)

            if material and prop and value:
                data.append(
                    {
                        'material': material, 'property': prop, 'value': value,
                        'conditions': record.get('conditions')
                    }
                )

        return data
