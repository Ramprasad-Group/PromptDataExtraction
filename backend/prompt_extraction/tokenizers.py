import pylogg
import numpy as np

log = pylogg.New("token")

class Tokenizer:
    """ Base tokenizer class to compute embeddings. """
    def __init__(self, model : str, device : int = 0) -> None:
        self.model = None
        self.tokenizer = None
        log.info("Initialized {}", self.__class__.__name__)

    def get_text_embeddings(self, text : str) -> np.array:
        raise NotImplementedError


class BertTokenizer(Tokenizer):
    def __init__(self, model : str, device : int = 0) -> None:
        super().__init__()

        # Load model and tokenizer
        from transformers import AutoTokenizer
        from transformers import AutoModelForTokenClassification

        t1 = log.trace("Loading bert model to device = {}.", device)
        self.tokenizer = AutoTokenizer.from_pretrained(model,
                                                       model_max_length=512)

        self.model = AutoModelForTokenClassification.from_pretrained(model)
        t1.done("Loaded bert model to device {}", device)


    def get_text_embeddings(self, text: str) -> np.array:
        """ Compute the embeddings for the given text.
            Returns a numpy array containing the text embeddings.
        """
        import torch

        # Tokenize the sentences
        encoded_inputs = self.tokenizer(text, padding=True, truncation=True,
                                        max_length=512, return_tensors='pt')

        # Obtain the embeddings from the model.
        # There may be more ways to do this,
        # can use the CLS token embedding as well.
        with torch.no_grad():
            outputs = self.model(**encoded_inputs)
            embeddings = outputs[0].mean(dim=1).squeeze(0)

        return embeddings.numpy()


class LlamaTokenizer(Tokenizer):
    def __init__(self, model : str, device : int = 0) -> None:
        super().__init__()

    def get_text_embeddings(self, text: str) -> np.array:
        """ Compute the embeddings for the given text.
            Returns a numpy array containing the text embeddings.
        """
        import polyai.api as polyai
        resp = polyai.TextEmbedding.create(
            model="polyai", # currently ignored by the server.
            text=text,
        )

        return np.array(resp['embeddings'])


class GPTTokenizer(Tokenizer):
    def __init__(self, model : str, device : int = 0) -> None:
        super().__init__()

        # Load model and tokenizer
        import tiktoken
        self.encoder = tiktoken.encoding_for_model(model)

    def get_text_embeddings(self, text: str) -> np.array:
        """ Compute the embeddings for the given text.
            Returns a numpy array containing the text embeddings.
        """
        return np.array(self.encoder.encode(text))

