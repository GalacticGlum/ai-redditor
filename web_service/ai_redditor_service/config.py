# GPT2 model configuration
GPT2_NO_CUDA = False
GPT2_QUANTIZE = False
GPT2_BOS_TOKEN = '<|bos|>'
GPT2_TRANSLATE_TOKEN = '<|eq_tok|>'
GPT2_END_OF_LIKES_TOKEN = '<|eol|>'

# Show debug information in the record generation task
RECORD_GENERATION_LOG_DEBUG_INFO = False

SQLALCHEMY_TRACK_MODIFICATIONS = False

# SocketIO configuration
SOCKETIO_ENABLE_LOGGING = False
ENGINEIO_ENABLE_LOGGING = False

# The client will send an AJAX request every 2.5 seconds
# asking about the status of the text generation task.
TASK_STATUS_TIMEOUT_MS = 2500 