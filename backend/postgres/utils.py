import uuid

def new_unique_key(*, prefix=""):
    """ Generate a new unique key using UUID. """
    return prefix + str(uuid.uuid4())
